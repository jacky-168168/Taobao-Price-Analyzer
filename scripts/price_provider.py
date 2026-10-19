"""安全且保守的淘寶商品級歷史報價解析器。

OneBound 的歷史 price 為文字，未保證是相同 SKU 的實付價。
本程式只匯入『商品級參考報價』，絕不寫入 paid 欄位。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api-gw.onebound.cn/taobao/item_history_price/"
MAX_ITEMS = 40
MAX_BODY = 3_000_000
MAX_PRICE = 10_000_000
CURRENT_RE = re.compile(r"(?:當前價|当前价|現價|现价)\s*[:：]\s*[¥￥]?\s*(\d{1,8}(?:\.\d{1,2})?)(?![\d.])")
PRICE_RE = re.compile(r"^\s*[¥￥]?\s*(\d{1,8}(?:\.\d{1,2})?)\s*元")
BARE_MONEY_RE = re.compile(r"^\s*[¥￥]\s*(\d{1,8}(?:\.\d{1,2})?)\s*$")
DATE_RE = re.compile(r"^(20\d{2}-\d{1,2}-\d{1,2})(?:\s+(\d{1,2}))?")


def require_id(value: object) -> str:
    result = str(value).strip()
    if not re.fullmatch(r"\d{6,20}", result):
        raise ValueError("商品 ID 必須是 6–20 位數字")
    return result


def parse_quote(raw: object) -> float | None:
    """只取明示價位；券規則、區間價、單件折算、付款價一律不推算。"""
    if not isinstance(raw, (str, int, float)):
        return None
    clean = html.unescape(re.sub(r"<[^>]*>", " ", str(raw))).strip()
    clean = re.sub(r"\s+", " ", clean)
    if re.match(r"^\s*[¥￥]?\s*\d+(?:\.\d+)?\s*[-~～至]\s*\d", clean):
        return None
    match = CURRENT_RE.search(clean) or PRICE_RE.search(clean) or BARE_MONEY_RE.match(clean)
    if not match:
        return None
    number = float(match.group(1))
    if not (0 < number <= MAX_PRICE):
        return None
    return round(number, 2)


def parse_date(raw: object, *, today: dt.date | None = None) -> tuple[str, int] | None:
    m = DATE_RE.match(str(raw).strip())
    if not m:
        return None
    try:
        d = dt.date.fromisoformat(m.group(1))
        hour = int(m.group(2) or 0)
        if hour > 23 or d > (today or dt.date.today()):
            return None
    except (ValueError, TypeError):
        return None
    return d.isoformat(), hour


def normalize_payload(payload: object, item_id: str, *, today: dt.date | None = None) -> list[dict]:
    """解析官方文件 items.item[]；保留同日最新小時一筆，不臆造缺失日期。"""
    if not isinstance(payload, dict):
        raise ValueError("API 回傳非 JSON 物件")
    obj = payload.get("items")
    if not isinstance(obj, dict) or not isinstance(obj.get("item"), list):
        raise ValueError("API 沒有預期的 items.item[]，可能是額度、權限或格式問題")
    response_id = obj.get("num_iid")
    if response_id and str(response_id) != item_id:
        raise ValueError(f"API 商品 ID 不符合要求：{item_id} vs {response_id}")
    by_date: dict[str, dict] = {}
    for entry in obj["item"]:
        if not isinstance(entry, dict):
            continue
        parsed = parse_date(entry.get("date"), today=today)
        price = parse_quote(entry.get("price"))
        if parsed is None or price is None:
            continue
        date, hour = parsed
        # 避免較舊的同日資料覆寫較新資料
        if date not in by_date or hour > by_date[date]["hour"]:
            by_date[date] = {"date": date, "hour": hour, "listed": price,
                             "source": "OneBound 商品級歷史報價", "scope": "item_only_unverified_sku",
                             "note": "僅供商品級參考；未核對 SKU、券資格、配送與實付"}
    return [by_date[d] for d in sorted(by_date)]


def fetch_onebound(item_id: str, key: str, secret: str, *, timeout: int = 25) -> dict:
    if not key or not secret:
        raise ValueError("請先配置 ONEBOUND_KEY 與 ONEBOUND_SECRET")
    params = urlencode({"key": key, "secret": secret, "num_iid": require_id(item_id),
                        "result_type": "json", "cache": "no"})
    req = Request(API_URL + "?" + params, headers={"User-Agent": "PersonalPriceResearch/1.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_BODY + 1)
    except (HTTPError, URLError, TimeoutError) as err:
        # 不印出 URL：URL 內有 API key/secret。
        raise RuntimeError(f"歷史價 API HTTP/網路錯誤 ({type(err).__name__})") from None
    if len(raw) > MAX_BODY:
        raise ValueError("API 回應超過預設上限")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("API 回傳非有效 JSON") from None


def collect(watchlist: list, existing: dict, fetcher, *, today: dt.date | None = None) -> dict:
    if not isinstance(watchlist, list) or len(watchlist) > MAX_ITEMS:
        raise ValueError(f"監控清單必須是陣列，最多 {MAX_ITEMS} 筆")
    prev = existing if isinstance(existing, dict) else {}
    products = {k: v for k, v in prev.get("products", {}).items()
                if re.fullmatch(r"\d{6,20}", str(k)) and isinstance(v, dict)}
    errors = {}
    for item in watchlist:
        try:
            if not isinstance(item, dict):
                raise ValueError("追蹤項目必須是物件")
            iid = require_id(item.get("item_id", ""))
            payload = fetcher(iid)
            points = normalize_payload(payload, iid, today=today)
            if not points:
                raise ValueError("沒有可確認的價格與日期，未改寫既有資料")
            before = products.get(iid, {}).get("observations", [])
            merged = {x["date"]: x for x in before if isinstance(x, dict) and x.get("date")}
            for x in points:
                if x["date"] not in merged or x["hour"] >= merged[x["date"]].get("hour", -1):
                    merged[x["date"]] = x
            products[iid] = {
                "name": str(item.get("name", ""))[:100],
                "observations": [merged[d] for d in sorted(merged)][-1000:],
            }
        except (ValueError, RuntimeError) as exc:
            # ID 不符等錯誤不阻止其他商品；不要移除成功的舊紀錄
            errors[str(item.get("item_id", "unknown")) if isinstance(item, dict) else "unknown"] = str(exc)
    return {"schema_version": 1,
            "updated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": "OneBound 商品級歷史報價；不是同一 SKU 實付價",
            "products": products, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="淘寶商品歷史參考報價同步；需自備 OneBound API 金鑰")
    parser.add_argument("--watchlist", default="config/watchlist.json")
    parser.add_argument("--out", default="data/provider_history.json")
    parser.add_argument("--fixture", default=None, help="僅測試用途：從測試 JSON 匯入，不呼叫實際 API")
    args = parser.parse_args()
    root = Path.cwd()
    watchlist = json.loads((root / args.watchlist).read_text(encoding="utf-8"))
    if not isinstance(watchlist, list):
        print("監控清單格式錯誤：必須是 JSON 陣列。", file=sys.stderr)
        return 2
    if not watchlist:
        print("監控清單是空陣列，已跳過同步；並未抓到任何商品價格。")
        return 0
    dest = root / args.out
    existing = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
    if args.fixture:
        fixture = json.loads((root / args.fixture).read_text(encoding="utf-8"))
        fetcher = lambda iid: fixture[iid]
    else:
        key, secret = os.getenv("ONEBOUND_KEY"), os.getenv("ONEBOUND_SECRET")
        if not key or not secret:
            print("尚未設定 ONEBOUND_KEY / ONEBOUND_SECRET，無法實際取得淘寶歷史價格。", file=sys.stderr)
            return 2
        fetcher = lambda iid: fetch_onebound(iid, key, secret)
    output = collect(watchlist, existing, fetcher)
    if output["errors"]:
        print("部分商品抓取失敗（不覆蓋舊資料）：" + json.dumps(output["errors"], ensure_ascii=False), file=sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已完成同步：{len(output['products'])} 商品，有錯誤 {len(output['errors'])} 筆")
    return 1 if output["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
