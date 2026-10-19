/* Taobao share-link parser. Offline only; does not pretend to resolve remote short URLs. */
(function(root){
'use strict';
const allowedHost=host=>['taobao.com','tmall.com','tb.cn'].some(base=>host===base||host.endsWith('.'+base));
function extractShare(raw){
 const text=String(raw||'').trim(),m=text.match(/https?:\/\/[^\s<>"'「」『』《》]+/i);if(!m)return {url:'',title:readTitle(text),itemId:null,isShort:false,error:'找不到淘寶或天貓網址'};
 let url=m[0].replace(/[，。！!、）)；;]+$/g,'');let u;
 try{u=new URL(url)}catch(e){return {url:'',title:readTitle(text),itemId:null,isShort:false,error:'網址格式不正確'}}
 if(!['https:','http:'].includes(u.protocol)||!allowedHost(u.hostname.toLowerCase())||u.username||u.password)return {url:'',title:readTitle(text),itemId:null,isShort:false,error:'僅支援淘寶／天貓的官方網址或 tb.cn 分享網址'};
 let id=null;for(const key of ['id','itemId','item_id','num_iid']){const v=u.searchParams.get(key);if(v&&/^\d{6,20}$/.test(v)){id=v;break}}
 if(!id){const path=u.pathname;const mm=path.match(/\/item\/(\d{6,20})(?:\.html?)?\/?$/i)||path.match(/\/i(?:tem)?(\d{6,20})(?:\.html?)?\/?$/i);id=mm?mm[1]:null}
 let isShort=(u.hostname.toLowerCase()==='tb.cn'||u.hostname.toLowerCase().endsWith('.tb.cn'))||/^\/h\./i.test(u.pathname);
 return {url:u.href,title:readTitle(text),itemId:id,isShort,error:null};
}
function readTitle(s){let m=s.match(/[「『]([^」』]{2,160})[」』]/)||s.match(/《([^》]{2,160})》/);return m?m[1].trim():''}
function normalizeSku(s){return String(s||'').trim().toLowerCase().replace(/[\s\u3000]+/g,'').replace(/[／/|、,，;；]+/g,'／')}
const api={extractShare,normalizeSku};if(typeof module==='object'&&module.exports)module.exports=api;root.TaobaoShareParser=api;
})(typeof globalThis!=='undefined'?globalThis:this);
