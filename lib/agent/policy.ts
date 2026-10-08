import rules from './policy_rules.json';
import type { Order,Customer,Verdict } from './types';
export const AS_OF='2026-10-07';
export const verdict=(decision:Verdict['decision'],amount=0,required_sources:string[]=[],code='MISSING_RECORD'):Verdict=>({decision,amount,required_sources,reason_codes:[code],as_of:AS_OF});
export function decide(o:Order|null,c:Customer|null):Verdict {
 if(!o||!c)return verdict('insufficient_evidence');
 if(c.risk_level==='high')return verdict('escalate',0,['fraud','escalation'],'FRAUD_HOLD');
 if(o.amount>rules.escalation.rules.max_refund_usd)return verdict('escalate',0,['escalation'],'VALUE_REQUIRES_REVIEW');
 if(o.category==='digital')return verdict('deny',0,['refund'],'DIGITAL_EXCLUDED');
 const days=(date:string)=>Math.round((Date.parse(AS_OF)-Date.parse(date))/86400000);
 if(o.category==='subscription') {const eligible=days(o.purchase_date)>=0&&days(o.purchase_date)<=rules.cancellation.rules.subscription_days&&o.condition==='unused';return verdict(eligible?'approve':'deny',eligible?o.amount:0,['cancellation'],eligible?'UNUSED_WITHIN_WINDOW':'SUBSCRIPTION_EXCLUDED');}
 if(o.status!=='delivered'||!o.delivery_date)return verdict('escalate',0,['shipping'],'DELIVERY_INVESTIGATION');
 const age=days(o.delivery_date);
 if(age<0||!Number.isFinite(age))return verdict('insufficient_evidence',0,['support'],'INVALID_DELIVERY_DATE');
 if(o.condition==='misuse')return verdict('deny',0,['returns','warranty'],'MISUSE_EXCLUDED');
 if(!['unopened','opened','defective'].includes(o.condition))return verdict('insufficient_evidence',0,['returns'],'UNKNOWN_CONDITION');
 const gold=c.tier==='Gold', sources=['refund',...(gold?['vip']:[])],window=gold?rules.vip.rules.gold_window_days:rules.refund.rules.window_days;
 if(age<=window){const factor=o.condition==='opened'?1-rules.refund.rules.restocking_rate:1;return verdict('approve',Math.round((o.amount*factor+Number.EPSILON)*100)/100,sources,factor<1?'RESTOCKING_FEE':'WITHIN_RETURN_WINDOW');}
 if(o.condition==='defective'&&age<=rules.warranty.rules.warranty_days)return verdict('warranty',0,['warranty',...sources],'WARRANTY_REPLACEMENT');
 return verdict('deny',0,[...sources,...(o.condition==='defective'?['warranty']:[])],'WINDOW_EXPIRED');
}
