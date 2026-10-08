import {retrieve} from './graph';
import {emptyUsage} from './provider';
import {now} from './store';
import cases from './retrieval-eval.json';
import type {RuntimeEnv,State} from './types';
export async function retrievalEvaluation(db:D1Database,env:RuntimeEnv,owner:string,mode:State['mode']|'keyword'){
 const usage=emptyUsage();const results:{id:string;query:string;relevant:string[];retrieved:string[];hit:boolean;recall:number;precision:number;mrr:number;latency_ms:number;passed:boolean;improvement:string}[]=[];const started=Date.now();
 for(const c of cases){const t=Date.now();const docs=await retrieve(db,env,owner,c.query,mode,usage);const ids=docs.slice(0,3).map(d=>d.id);const hits=c.relevant.filter(id=>ids.includes(id));const rank=docs.findIndex(d=>c.relevant.includes(d.id));results.push({...c,retrieved:ids,hit:hits.length>0,recall:hits.length/c.relevant.length,precision:hits.length/3,mrr:rank<0?0:1/(rank+1),latency_ms:Date.now()-t,passed:hits.length===c.relevant.length,improvement:'Inspect chunk boundaries and competing results. Compare semantic/hybrid retrieval against this frozen baseline; do not add expected sources before scoring.'});}
 const mean=(k:'recall'|'precision'|'mrr')=>results.reduce((s,r)=>s+r[k],0)/results.length;
 return {kind:'retrieval',mode,retrieval_method:mode==='live'?'Provider embeddings':mode==='keyword'?'Keyword baseline':'Local semantic embeddings',k:3,case_count:results.length,generated_at:now(),hit_rate:results.filter(r=>r.hit).length/results.length,recall:mean('recall'),precision:mean('precision'),mrr:mean('mrr'),latency_ms:Date.now()-started,usage,results,scope:'Synthetic, manually labelled policy queries; independent retrieval ranking before policy evidence completion. Not LLM or ML accuracy.'};
}
export const retrievalCases=cases;
