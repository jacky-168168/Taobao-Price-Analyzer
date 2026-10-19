import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from price_provider import collect, normalize_payload, parse_date, parse_quote, require_id

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'onebound_sample.json').read_text(encoding='utf-8'))
TODAY = dt.date(2026, 10, 19)

class ProviderTests(unittest.TestCase):
    def test_item_id_validation(self):
        self.assertEqual(require_id('817241051574'), '817241051574')
        for bad in ('https://evil.com', '123', '0000&key=secret', 'x'*80):
            with self.assertRaises(ValueError):
                require_id(bad)

    def test_parse_quote_does_not_treat_coupon_as_price(self):
        self.assertEqual(parse_quote('33.41元（合5.57元/件）'), 33.41)
        self.assertEqual(parse_quote('<p>当前价:33.4</p><p>优惠券：满33减23</p>'), 33.4)
        self.assertIsNone(parse_quote('優惠券：滿100減20'))
        self.assertIsNone(parse_quote('¥40-¥80'))
        self.assertIsNone(parse_quote(''))
        self.assertIsNone(parse_quote('0元'))

    def test_date_rejection(self):
        self.assertIsNone(parse_date('2026-02-30 10', today=TODAY))
        self.assertIsNone(parse_date('2026-11-11 10', today=TODAY))
        self.assertIsNone(parse_date('2026-10-10 25', today=TODAY))
        self.assertEqual(parse_date('2026-10-10 01', today=TODAY), ('2026-10-10', 1))

    def test_history_is_reference_not_paid(self):
        rows = normalize_payload(FIXTURE, '817241051574', today=TODAY)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all('paid' not in x and x['scope'] == 'item_only_unverified_sku' for x in rows))
        self.assertEqual([x['listed'] for x in rows], [33.41, 5.07, 35.42, 33.4])
        self.assertEqual(rows[2]['hour'], 19)

    def test_id_mismatch(self):
        with self.assertRaises(ValueError):
            normalize_payload(FIXTURE, '111111111', today=TODAY)

    def test_failure_preserves_previous_good_history(self):
        old = {'products': {'817241051574': {'observations': [{'date':'2026-09-01','hour':0,'listed': 52}]}}}
        output = collect([{'item_id':'817241051574'}], old, lambda _: (_ for _ in ()).throw(ValueError('API 額度不足')), today=TODAY)
        self.assertEqual(output['products'], old['products'])
        self.assertIn('817241051574', output['errors'])

    def test_collect_merge_and_deduplicate(self):
        out = collect([{'item_id':'817241051574', 'name':'測試商品'}], {}, lambda _: FIXTURE, today=TODAY)
        self.assertEqual(len(out['products']['817241051574']['observations']), 4)
        out2 = collect([{'item_id':'817241051574', 'name':'測試商品'}], out, lambda _: FIXTURE, today=TODAY)
        self.assertEqual(len(out2['products']['817241051574']['observations']), 4)

    def test_invalid_response_is_not_silently_used(self):
        with self.assertRaises(ValueError):
            normalize_payload({'error':'no access'}, '817241051574', today=TODAY)

if __name__ == '__main__':
    unittest.main()
