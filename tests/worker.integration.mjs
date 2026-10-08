import { createRequire } from 'node:module';
import { readFile,readdir,writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {Miniflare}=require(require.resolve('miniflare',{paths:[require.resolve('wrangler/package.json')]}));
const root=path.resolve('dist/server');
const files=await readdir(root,{recursive:true});
const modules=['index.js',...files.filter(f=>f!=='index.js'&&/\.(js|mjs)$/.test(f))].map(f=>({type:'ESModule',path:path.join(root,f)}));
const mf=new Miniflare({modules,modulesRoot:root,compatibilityDate:'2026-05-15',compatibilityFlags:['nodejs_compat'],d1Databases:{DB:'compiled-worker-test'}});
try{
 const db=await mf.getD1Database('DB');for(const f of (await readdir('drizzle')).filter(f=>f.endsWith('.sql')).sort())for(const sql of (await readFile('drizzle/'+f,'utf8')).split('--> statement-breakpoint'))if(sql.trim())await db.prepare(sql).run();
 const h=await mf.dispatchFetch('http://localhost/api/health');assert.equal(h.status,200);assert.equal((await h.json()).runtime,'LangGraph TypeScript on Workers');const cookie=h.headers.get('set-cookie').split(';')[0];
 const headers={cookie,'Content-Type':'application/json',origin:'http://localhost'};
 const create=await mf.dispatchFetch('http://localhost/api/runs',{method:'POST',headers,body:JSON.stringify({task:'Review NS-1044 refund',mode:'rules'})});assert.equal(create.status,201);const run=await create.json();
 const execute=await mf.dispatchFetch('http://localhost/api/runs/'+run.id+'/execute',{method:'POST',headers,body:'{}'});assert.equal(execute.status,200);const done=await execute.json();assert.equal(done.status,'awaiting_review');assert.equal(done.state.answer.amount,85);
 const cpCreate=await mf.dispatchFetch('http://localhost/api/runs',{method:'POST',headers,body:JSON.stringify({task:'Review complaint CP-101',mode:'rules'})});
 const cp=await cpCreate.json();const cpExecute=await mf.dispatchFetch('http://localhost/api/runs/'+cp.id+'/start',{method:'POST',headers,body:'{}'});assert.equal(cpExecute.status,202);let cpDone;for(let attempt=0;attempt<40;attempt++){const poll=await mf.dispatchFetch('http://localhost/api/runs/'+cp.id,{headers});cpDone=await poll.json();if(!['queued','running'].includes(cpDone.status))break;await new Promise(r=>setTimeout(r,100));}assert.equal(cpDone.state.ml_prediction.status,'scored');assert.equal(cpDone.status,'awaiting_review');assert.equal(cpDone.state.escalation_prediction.model_version,'synthetic-escalation-v1');assert.equal(cpDone.state.escalation_prediction.synthetic_training,true);assert.equal(cpDone.state.financial_customer.name,'Emma Chen');assert.equal(cpDone.state.answer.decision,'escalate');
 const review=await mf.dispatchFetch('http://localhost/api/runs/'+cp.id+'/review',{method:'POST',headers,body:JSON.stringify({decision:'approve',revision:cpDone.revision,answer:cpDone.state.answer.customer_reply})});assert.equal(review.status,200);assert.equal((await review.json()).status,'approved');const saved=await mf.dispatchFetch('http://localhost/api/runs/'+cp.id,{headers});assert.equal((await saved.json()).status,'approved');
 const mcp=await mf.dispatchFetch('http://localhost/mcp',{method:'POST',headers,body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list'})});assert.equal(mcp.status,200);assert.equal((await mcp.json()).result.tools.length,8);
 const model=await mf.dispatchFetch('http://localhost/api/ml/evaluation');assert.equal((await model.json()).split.test.rows,4000);
 const page=await mf.dispatchFetch('http://localhost/');assert.equal(page.status,200);const html=await page.text();assert.match(html,/Complaint register/);assert.match(html,/CP-101/);assert.match(html,/High-value refund with conflicting evidence/);assert.match(html,/Run demo case/);assert.doesNotMatch(html,/Loading the complaint register/);
 const report={verified_at:new Date().toISOString(),compiled_worker:true,checks:['Production Worker imports and starts in workerd','D1 bindings and schema work in compiled build','Compiled LangGraph produces correct restocking-fee result','Homepage server-renders successfully','Compiled Worker calls both trained ML artifacts through actual LangGraph; linked Emma Chen case escalates','Model evaluation endpoint returns temporal test evidence','Background start, polling and explicit human approval persist in D1','Hosted MCP discovery exposes eight tools'],visual_browser_qa:false,real_model_verified:false};await writeFile('verification/worker.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}finally{await mf.dispose();}
