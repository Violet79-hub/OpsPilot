import {escalationReport,predictEscalation} from './escalation';
import semanticEvidence from '../../verification/semantic.json';
import releaseReport from '../../verification/release.json';
import modelRelease from '../../verification/model-release.json';
import {caseFile,complaintRecord,changeCase,caseChange} from './casefile';
import {mlReport,predictResponseDelay,complaintSchema} from './ml';
import {retrievalEvaluation,retrievalCases} from './quality';
import { z } from 'zod';
import { seedDB,getRun,getDocs,event,id,now,quota } from './store';
import { runGraph,retrieve,chunkText } from './graph';
import { emptyUsage } from './provider';
import type { RuntimeEnv,State,Run } from './types';
import golden from './golden.json';
import complaintGolden from './complaint-golden.json';
class HttpError extends Error {constructor(public code:number,message:string){super(message);}}
const publicState=(raw:string)=>{const state=JSON.parse(raw) as State;if(state.sources)state.sources=state.sources.map(doc=>({...doc,owner:doc.trusted?'global':'private',embedding:null}));return state;};
const clean=(r:Run)=>({id:r.id,task:r.task,mode:r.mode,status:r.status,state:publicState(r.state),revision:r.revision,created:r.created,updated:r.updated});
async function body(req:Request){const text=await req.text();if(text.length>80000)throw new HttpError(413,'Request too large');try{return JSON.parse(text);}catch{throw new HttpError(400,'Invalid JSON');}}
export async function api(request:Request,env:RuntimeEnv,ctx?:{waitUntil:(task:Promise<unknown>)=>void}):Promise<Response>{
 const url=new URL(request.url),path=url.pathname.replace(/\/$/,'');
 const existing=request.headers.get('cookie')?.match(/(?:^|; )opspilot_session=([0-9a-f-]{36})(?:;|$)/)?.[1];
 const owner=existing||id();const headers:Record<string,string>={'Cache-Control':'no-store','Content-Type':'application/json','X-Content-Type-Options':'nosniff'};
 if(!existing)headers['Set-Cookie']=`opspilot_session=${owner}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000${url.protocol==='https:'?'; Secure':''}`;
 const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers});
 try {
  if(!['GET','HEAD'].includes(request.method)){
   const origin=request.headers.get('origin');if(origin&&origin!==url.origin)throw new HttpError(403,'Cross-origin write refused');
   if(request.headers.get('sec-fetch-site')==='cross-site')throw new HttpError(403,'Cross-site write refused');
   if(!request.headers.get('content-type')?.startsWith('application/json'))throw new HttpError(415,'Use application/json');
  }
  const db=env.DB;if(!db)throw new HttpError(503,'Database binding is not configured');await seedDB(db);
  const requireModel=()=>{if(!env.OPENAI_API_KEY)throw new HttpError(503,'MODEL_NOT_CONFIGURED: The owner must connect an OpenAI API key. No simulated model response is used.');};
  if(path==='/api/releases'&&request.method==='GET')return json({pipeline:releaseReport,model:modelRelease});
  if(path==='/api/health')return json({status:'ok',database:'D1 SQLite',model_configured:!!env.OPENAI_API_KEY,model:env.OPENAI_MODEL||'gpt-4o-mini',embedding_model:'text-embedding-3-small',embedding_dimensions:512,fixture_date:'2026-10-07',runtime:'LangGraph TypeScript on Workers',persistence:'server',payment_execution:false});
  const caseMatch=path.match(/^\/api\/complaints\/(CP-\d{3,8})\/casefile$/);
  if(caseMatch){if(!await complaintRecord(db,owner,caseMatch[1]))throw new HttpError(404,'Case not found');if(request.method==='GET')return json(await caseFile(db,owner,caseMatch[1]));if(request.method==='POST'){await quota(db,'casefile:'+owner+':'+now().slice(0,10),100);const result=await changeCase(db,owner,caseMatch[1],caseChange.parse(await body(request)));return json(result.data||{error:result.error},result.status);}}
  if(path==='/api/ml/evaluation')return json(mlReport);
  if(path==='/api/complaints'&&request.method==='GET'){const rows=await db.prepare("SELECT body FROM records WHERE kind='complaints' OR kind=? ORDER BY CASE WHEN kind='complaints' THEN 1 ELSE 0 END, CASE WHEN json_extract(body,'$.synthetic')=1 THEN 0 ELSE 1 END,id").bind('complaints:'+owner).all<{body:string}>();headers['X-OpsPilot-Data-Source']='d1';return json(rows.results.map(r=>JSON.parse(r.body)));}
  if(path==='/api/complaints'&&request.method==='POST'){
   const input=z.object({summary:z.string().trim().min(10).max(4000),features:complaintSchema}).strict().parse(await body(request));await quota(db,'complaints:'+owner+':'+now().slice(0,10),30);
   const key='CP-'+String(1000000+crypto.getRandomValues(new Uint32Array(1))[0]%9000000);const record={id:key,...input,created:now(),source:'Session-private analyst submission; unverified complaint details'};
   await db.prepare('INSERT INTO records(id,kind,body) VALUES(?,?,?)').bind(key,'complaints:'+owner,JSON.stringify(record)).run();return json(record,201);
  }
  if(path==='/api/ml/escalation/evaluation')return json(escalationReport);
  if(path==='/api/ml/escalation/predict'&&request.method==='POST'){const input=z.object({case_id:z.string().regex(/^CP-\d{3,8}$/)}).strict().parse(await body(request));const prediction=await predictEscalation(db,owner,input.case_id);if(!prediction)throw new HttpError(404,'Linked financial records unavailable');return json(prediction);}
  if(path==='/api/ml/predict'&&request.method==='POST')return json(predictResponseDelay(await body(request)));
  if(path==='/api/retrieval/comparison')return json(semanticEvidence);
  if(path==='/api/retrieval/cases')return json(retrievalCases);
  if(path==='/api/retrieval/evaluations'&&request.method==='GET')return json((await db.prepare('SELECT body FROM records WHERE kind=? ORDER BY id DESC LIMIT 10').bind('retrieval_eval:'+owner).all<{body:string}>()).results.map(r=>JSON.parse(r.body)));
  if(path==='/api/retrieval/evaluations'&&request.method==='POST'){
   const input=z.object({mode:z.enum(['rules','live','keyword'])}).parse(await body(request));if(input.mode==='live')requireModel();
   await quota(db,'retrieval_eval:'+owner+':'+now().slice(0,10),10);
   const report=await retrievalEvaluation(db,env,owner,input.mode);const key=now()+':'+id();await db.prepare('INSERT INTO records(id,kind,body) VALUES(?,?,?)').bind(key,'retrieval_eval:'+owner,JSON.stringify(report)).run();return json({id:key,...report},201);
  }
  if(path==='/api/monitoring'){
   const rows=(await db.prepare('SELECT * FROM runs WHERE owner=? ORDER BY created DESC LIMIT 500').bind(owner).all<Run>()).results.map(clean);
   const batches=(await db.prepare('SELECT mode,results FROM batches WHERE owner=? ORDER BY created DESC LIMIT 10').bind(owner).all<{mode:string;results:string}>()).results;
   const latency=rows.map(r=>r.state.latency_ms).filter((v):v is number=>typeof v==='number').sort((a,b)=>a-b);
   const failures=rows.filter(r=>r.status==='failed'||r.status==='blocked').map(r=>({run_id:r.id,task:r.task,status:r.status,mode:r.mode,category:r.state.error?'System / provider failure':r.state.answer?.decision==='insufficient_evidence'?'Insufficient evidence':'Decision validation failure',reason:r.state.error||r.state.verdict?.reason_codes.join(', ')||'Validation failed',checks:r.state.checks,improvement:r.state.error?'Check provider availability, request limits and recorded tool inputs; retry only after resolving the cause.':'Collect missing matching business records or investigate failed validations. Keep external actions blocked.'}));
   return json({scope:'Current anonymous browser session; latest 500 runs and 10 evaluation batches',run_count:rows.length,completed:rows.filter(r=>['awaiting_review','approved','rejected'].includes(r.status)).length,failed:rows.filter(r=>r.status==='failed').length,blocked:rows.filter(r=>r.status==='blocked').length,p50_latency_ms:latency.length?latency[Math.floor((latency.length-1)*.5)]:null,p95_latency_ms:latency.length?latency[Math.ceil((latency.length-1)*.95)]:null,usage:rows.reduce((a,r)=>({input_tokens:a.input_tokens+(r.state.usage?.input_tokens||0),output_tokens:a.output_tokens+(r.state.usage?.output_tokens||0),embedding_tokens:a.embedding_tokens+(r.state.usage?.embedding_tokens||0)}),emptyUsage()),estimated_cost_usd:rows.some(r=>r.mode==='live')?null:0,average_provider_cost_usd:rows.some(r=>r.mode==='live')?null:rows.length?0:null,cost_status:rows.some(r=>r.mode==='live')?'Provider token usage is recorded; currency cost unavailable until verified price configuration.':'Recorded local-mode runs make no provider requests: provider API spend is $0. Hosting and compute costs are excluded.',failures,latest_evaluations:batches.map(b=>{const rs=JSON.parse(b.results) as {passed:boolean;checks?:Record<string,boolean>;latency_ms?:number;retrieval_recall?:number;tool_execution_success?:number}[];const mean=(key:string)=>rs.length?rs.reduce((sum,r)=>sum+(r.checks?.[key]?1:0),0)/rs.length:null;return {mode:b.mode,case_count:rs.length,pass_rate:rs.length?rs.filter(r=>r.passed).length/rs.length:null,decision_accuracy:mean('decision'),policy_compliance:mean('guardrails'),source_accuracy:mean('sources'),tool_coverage_accuracy:mean('tools'),scope:'Expected tool coverage, not proof of autonomous model tool selection'};})});
  }
  if(path==='/api/runs'&&request.method==='GET'){const rows=(await db.prepare('SELECT * FROM runs WHERE owner=? ORDER BY created DESC LIMIT 100').bind(owner).all<Run>()).results;return json(rows.map(clean));}
  if(path==='/api/runs'&&request.method==='POST'){
   const input=z.object({task:z.string().trim().min(5).max(2000),mode:z.enum(['live','rules']).default('live')}).parse(await body(request));if(input.mode==='live')requireModel();
   await quota(db,`runs:${owner}:${now().slice(0,10)}`,100);
   const key=id(),time=now();await db.prepare('INSERT INTO runs(id,owner,task,mode,status,state,created,updated) VALUES(?,?,?,?,?,?,?,?)').bind(key,owner,input.task,input.mode,'queued',JSON.stringify(input),time,time).run();
   return json(clean((await getRun(db,key,owner))!),201);
  }
  const match=path.match(/^\/api\/runs\/([0-9a-f-]{36})(?:\/(execute|review|events|start))?$/);
  if(match){
   const key=match[1],action=match[2];let run=await getRun(db,key,owner);if(!run)throw new HttpError(404,'Run not found in this session');
   if(run.status==='running'&&Date.now()-Date.parse(run.updated)>180000){await db.prepare("UPDATE runs SET status='failed',state=?,updated=? WHERE id=? AND owner=? AND status='running' AND updated=?").bind(JSON.stringify({...JSON.parse(run.state),error:'Execution was interrupted. Submit a new task to retry.'}),now(),key,owner,run.updated).run();run=(await getRun(db,key,owner))!;}
   if(!action&&request.method==='GET')return json(clean(run));
   if(action==='events'&&request.method==='GET')return json((await db.prepare('SELECT id,node,body,created FROM events WHERE run_id=? ORDER BY id').bind(key).all()).results.map(r=>({...r,body:JSON.parse(String(r.body))})));
   if(action==='start'&&request.method==='POST'){
    if(run.mode==='live')requireModel();if(!['queued','running'].includes(run.status))throw new HttpError(409,'This assessment has already finished. Create a new assessment.');
    if(run.status==='queued'){const target=new URL(request.url);target.pathname=target.pathname.replace(/\/start$/,'/execute');const worker=api(new Request(target.toString(),{method:'POST',headers:request.headers,body:'{}'}),env);if(ctx)ctx.waitUntil(worker);else await worker;}
    return json({id:key,status:'accepted',poll:'/api/runs/'+key},202);
   }
   if(action==='execute'&&request.method==='POST'){
    if(run.mode==='live')requireModel();
    const claimed=await db.prepare("UPDATE runs SET status='running',updated=? WHERE id=? AND owner=? AND status='queued' RETURNING id").bind(now(),key,owner).first();if(!claimed)throw new HttpError(409,'This run has already started. Refresh to view its result.');
    try{if(run.mode==='live')await quota(db,`model:${now().slice(0,10)}`,Math.max(1,Math.min(500,Number(env.MODEL_DAILY_LIMIT)||100)));await runGraph(db,env,owner,key,JSON.parse(run.state));}
    catch(error){const current=await getRun(db,key,owner);if(current?.status==='running'){await db.prepare("UPDATE runs SET status='failed',state=?,updated=? WHERE id=?").bind(JSON.stringify({...JSON.parse(current.state),error:error instanceof Error?error.message:'Execution failed'}),now(),key).run();}return json(clean((await getRun(db,key,owner))!));}
    return json(clean((await getRun(db,key,owner))!));
   }
   if(action==='review'&&request.method==='POST'){
    const input=z.object({decision:z.enum(['approve','reject']),revision:z.number().int().min(0),answer:z.string().trim().min(10).max(5000)}).parse(await body(request));const state:State=JSON.parse(run.state);
    if(state.plan?.complaint_id){const current=await caseFile(db,owner,state.plan.complaint_id);if(current.stage==='waiting_for_information'||current.revision!==(state.complaint_revision||0))throw new HttpError(409,'Case evidence changed or information is pending. Run a new assessment before review.');}
    if(run.status!=='awaiting_review'||!state.checks?.every(c=>c.passed)||state.answer?.decision==='insufficient_evidence')throw new HttpError(409,'This run is not eligible for approval');
    const reviewId=id(),time=now(),nextStatus=input.decision==='approve'?'approved':'rejected';
    const statements=[db.prepare("INSERT OR IGNORE INTO reviews(id,run_id,owner,decision,answer,created) SELECT ?,id,owner,?,?,? FROM runs WHERE id=? AND owner=? AND status='awaiting_review' AND revision=? AND (? IS NULL OR NOT EXISTS(SELECT 1 FROM records WHERE id=? AND (json_extract(body,'$.revision')!=? OR json_extract(body,'$.stage')='waiting_for_information')))").bind(reviewId,input.decision,input.answer,time,key,owner,input.revision,state.plan?.complaint_id||null,'casefile:'+owner+':'+(state.plan?.complaint_id||''),state.complaint_revision||0)];
    if(input.decision==='approve')statements.push(db.prepare('INSERT OR IGNORE INTO actions(id,run_id,owner,body,created) SELECT ?,run_id,owner,?,? FROM reviews WHERE id=?').bind(id(),JSON.stringify({type:'internal_support_recommendation',decision:state.verdict!.decision,amount:state.verdict!.amount,customer_reply:input.answer,external_payment:false}),time,reviewId));
    statements.push(db.prepare("UPDATE runs SET status=?,revision=revision+1,updated=?,state=json_set(state,'$.reviewed_reply',?) WHERE id=? AND owner=? AND EXISTS(SELECT 1 FROM reviews WHERE id=?)").bind(nextStatus,time,input.answer,key,owner,reviewId));
    const result=await db.batch(statements);if(!result[0].meta.changes)throw new HttpError(409,'Review conflict. Another review already changed this run.');
    await event(db,key,'human_review',{decision:input.decision,edited:input.answer!==state.answer!.customer_reply,revision:input.revision+1,action_created:input.decision==='approve'});return json(clean((await getRun(db,key,owner))!));
   }
  }
  if(path==='/api/documents'&&request.method==='GET')return json((await getDocs(db,owner)).map(({embedding,...doc})=>({...doc,owner:doc.trusted?'global':'private',indexed:!!embedding,embedding_status:'Local static embeddings available on demand',document_version:'demo-1',chunks:doc.chunks||chunkText(doc.body).map((text,index)=>({id:doc.id+':chunk:'+index,section:doc.name.match(/§([0-9.]+)/)?.[1]||'Full policy',text,start:index*1400,end:index*1400+text.length}))})));
  if(path==='/api/documents'&&request.method==='POST'){
   const input=z.object({name:z.string().trim().min(1).max(120),text:z.string().trim().min(20).max(16000)}).parse(await body(request));const count=await db.prepare('SELECT COUNT(*) AS n FROM documents WHERE owner=?').bind(owner).first<{n:number}>();if((count?.n||0)>=20)throw new HttpError(429,'Maximum 20 reference documents per session');
   const key=id();await db.prepare('INSERT INTO documents(id,owner,name,body,trusted,created) VALUES(?,?,?,?,0,?)').bind(key,owner,input.name,input.text,now()).run();return json({id:key,name:input.name,trusted:false,indexed:false},201);
  }
  if(path==='/api/search'&&request.method==='POST'){
   const input=z.object({query:z.string().min(2).max(1000),mode:z.enum(['live','rules','keyword'])}).parse(await body(request));if(input.mode==='live'){requireModel();await quota(db,`search:${now().slice(0,10)}`,200);}const usage=emptyUsage();return json({sources:(await retrieve(db,env,owner,input.query,input.mode,usage)).map(({embedding,...doc})=>({...doc,owner:doc.trusted?'global':'private',indexed:!!embedding,embedding_status:'Local static embeddings available on demand',document_version:'demo-1',chunks:doc.chunks||chunkText(doc.body).map((text,index)=>({id:doc.id+':chunk:'+index,section:doc.name.match(/§([0-9.]+)/)?.[1]||'Full policy',text,start:index*1400,end:index*1400+text.length}))})),usage,method:input.mode==='keyword'?'keyword':'semantic'});
  }
  if(path==='/api/orders'&&request.method==='GET')return json((await db.prepare("SELECT body FROM records WHERE kind='orders' ORDER BY id").all<{body:string}>()).results.map(r=>JSON.parse(r.body)));
  if(path==='/api/actions'&&request.method==='GET')return json((await db.prepare('SELECT id,run_id,body,created FROM actions WHERE owner=? ORDER BY created DESC LIMIT 100').bind(owner).all()).results.map(r=>({...r,body:JSON.parse(String(r.body))})));
  if(path==='/api/evaluations'&&request.method==='GET')return json((await db.prepare('SELECT id,mode,results,created FROM batches WHERE owner=? ORDER BY created DESC LIMIT 10').bind(owner).all()).results.map(r=>({...r,results:JSON.parse(String(r.results))})));
  if(path==='/api/dataset'&&request.method==='GET')return json(url.searchParams.get('scope')==='complaints'?complaintGolden:golden);
  if(path==='/api/evaluations'&&request.method==='POST'){
   const input=z.object({mode:z.enum(['live','rules']),case_ids:z.array(z.string()).min(1).max(30)}).parse(await body(request));if(input.mode==='live')requireModel();
   if(input.mode==='live'&&input.case_ids.length>3)throw new HttpError(400,'Live batches support up to 3 cases to keep execution bounded');
   await quota(db,`eval:${owner}:${now().slice(0,10)}`,10);
   const cases=[...golden,...complaintGolden].filter(c=>input.case_ids.includes(c.id));if(cases.length!==new Set(input.case_ids).size)throw new HttpError(400,'Unknown case ID');
   const results=[];
   for(const c of cases){
    if(input.mode==='live')await quota(db,`model:${now().slice(0,10)}`,Math.max(1,Math.min(500,Number(env.MODEL_DAILY_LIMIT)||100)));
    const key=id(),time=now(),initial:State={task:c.task,mode:input.mode};await db.prepare('INSERT INTO runs(id,owner,task,mode,status,state,created,updated) VALUES(?,?,?,?,?,?,?,?)').bind(key,owner,c.task,input.mode,'running',JSON.stringify(initial),time,time).run();
    try{const state=await runGraph(db,env,owner,key,initial);const a=state.answer!;const checks={synthetic_risk_contract:'expected_probability_range' in c?!!state.escalation_prediction&&state.escalation_prediction.risk_probability>=0&&state.escalation_prediction.risk_probability<=1:true,escalation:'expected_escalation_status' in c?(a.decision==='escalate')===c.expected_escalation_status:true,model:'expected_model_status' in c?(state.ml_prediction?.status||'none')===c.expected_model_status:true,decision:a.decision===c.expected_decision,amount:a.amount>=c.expected_refund_range[0]&&a.amount<=c.expected_refund_range[1],sources:c.expected_sources.every(s=>a.citations.includes(s)),tools:c.expected_tools.every(t=>state.tools!.some(x=>x.name===t)),guardrails:state.checks!.every(x=>x.passed)};results.push({case_id:c.id,run_id:key,passed:Object.values(checks).every(Boolean),checks,latency_ms:state.latency_ms,usage:state.usage,retrieved_ids:state.retrieved_ids,retrieval_recall:c.expected_sources.length?c.expected_sources.filter(id=>state.retrieved_ids?.includes(id)).length/c.expected_sources.length:null,tool_execution_success:state.tools?.length?state.tools.filter(t=>t.output!==null).length/state.tools.length:null});}
    catch(error){results.push({case_id:c.id,run_id:key,passed:false,error:error instanceof Error?error.message:'Execution failed'});}
   }
   const batchId=id(),created=now();await db.prepare('INSERT INTO batches(id,owner,mode,results,created) VALUES(?,?,?,?,?)').bind(batchId,owner,input.mode,JSON.stringify(results),created).run();return json({id:batchId,mode:input.mode,results,created},201);
  }
  throw new HttpError(404,'Endpoint not found');
 }catch(error){if(error instanceof HttpError)return json({error:error.message},error.code);if(error instanceof z.ZodError)return json({error:'Invalid request',issues:error.issues.map(x=>({path:x.path,message:x.message}))},400);return json({error:error instanceof Error?error.message:'Server error'},500);}
}
