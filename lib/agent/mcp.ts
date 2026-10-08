import {financialTool} from './financial';
import {predictEscalation} from './escalation';
import {semanticRank} from './semantic';
import {z} from 'zod';
import {complaintSchema,predictResponseDelay,mlReport} from './ml';
import {getDocs,seedDB,quota,now} from './store';
import {complaintRecord} from './casefile';
import type {RuntimeEnv} from './types';
const fields=['product','sub_product','issue','sub_issue','submitted_via','company_key'];
export const mcpTools=[
 ...['get_customer','get_transaction','get_account','predict_escalation_risk'].map(name=>({name,description:name==='predict_escalation_risk'?'Synthetic-trained escalation model, shadow-only. Not validated on real financial outcomes.':'Read the record linked to an accessible complaint; linkage and identity are checked.',inputSchema:{type:'object',properties:{case_id:{type:'string',pattern:'^CP-[0-9]{3,8}$'}},required:['case_id'],additionalProperties:false}})),
 {name:'get_complaint',description:'Read a complaint accessible to this execution context. Browser-private cases are not shared with external MCP sessions.',inputSchema:{type:'object',properties:{id:{type:'string',pattern:'^CP-[0-9]{3,8}$'}},required:['id'],additionalProperties:false}},
 {name:'predict_response_delay',description:'Run the versioned historical complaint-delay model. Shadow-only; may abstain. Does not authorise money movement.',inputSchema:{type:'object',properties:Object.fromEntries(fields.map(k=>[k,{type:'string'}])),required:fields,additionalProperties:false}},
 {name:'search_company_policy',description:'Retrieve policy excerpts and IDs. Policies are synthetic internal demo material, not legal advice.',inputSchema:{type:'object',properties:{query:{type:'string'},limit:{type:'integer',minimum:1,maximum:6}},required:['query'],additionalProperties:false}},
 {name:'get_model_card',description:'Read the trained model evaluation, dataset lineage and limitations.',inputSchema:{type:'object',properties:{},additionalProperties:false}}
].map(t=>({...t,annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false}}));
const envelope=z.object({jsonrpc:z.literal('2.0'),id:z.union([z.string(),z.number()]).optional(),method:z.string(),params:z.record(z.unknown()).optional()}).strict();
export async function dispatchMcp(raw:unknown,db:D1Database,owner:string|null){
 const parsed=envelope.safeParse(raw);if(!parsed.success)return {jsonrpc:'2.0',id:null,error:{code:-32600,message:'Invalid JSON-RPC request'}};
 const m=parsed.data;const ok=(result:unknown)=>({jsonrpc:'2.0',id:m.id??null,result});const error=(code:number,message:string)=>({jsonrpc:'2.0',id:m.id??null,error:{code,message}});
 if(m.method==='notifications/initialized')return null;
 if(m.id===undefined)return null;
 if(m.method==='initialize')return ok({protocolVersion:'2025-03-26',capabilities:{tools:{listChanged:false}},serverInfo:{name:'OpsPilot complaint tools',version:'5.0.0'},instructions:'Read-only complaint investigation. Browser session data is separate from external MCP identity.'});
 if(m.method==='ping')return ok({});
 if(m.method==='tools/list')return ok({tools:mcpTools});
 if(m.method!=='tools/call')return error(-32601,'Method not found');
 if(!owner)return error(-32001,'Authenticated execution context required');
 const call=z.object({name:z.string(),arguments:z.record(z.unknown()).default({})}).safeParse(m.params);if(!call.success)return error(-32602,'Invalid tool arguments');
 try{
  let result:unknown;const {name,arguments:args}=call.data;
  if(['get_customer','get_transaction','get_account','predict_escalation_risk'].includes(name)){const input=z.object({case_id:z.string().regex(/^CP-\d{3,8}$/)}).strict().parse(args);result=name==='predict_escalation_risk'?await predictEscalation(db,owner,input.case_id):await financialTool(db,owner,input.case_id,name);if(!result)return ok({isError:true,content:[{type:'text',text:'Linked record unavailable in this context'}]});}
  else if(name==='get_complaint'){const input=z.object({id:z.string().regex(/^CP-\d{3,8}$/)}).strict().parse(args);result=await complaintRecord(db,owner,input.id);if(!result)return ok({isError:true,content:[{type:'text',text:'Complaint not found in this context'}]});}
  else if(name==='predict_response_delay')result=predictResponseDelay(complaintSchema.parse(args));
  else if(name==='get_model_card'){z.object({}).strict().parse(args);result=mlReport;}
  else if(name==='search_company_policy'){const input=z.object({query:z.string().trim().min(2).max(1000),limit:z.number().int().min(1).max(6).default(3)}).strict().parse(args);result=semanticRank(await getDocs(db,owner),input.query).slice(0,input.limit).map(d=>({id:d.id,name:d.name,trusted:!!d.trusted,text:d.body,score:d.score,chunks:d.chunks}));}
  else return error(-32602,'Unknown tool');
  return ok({isError:false,content:[{type:'text',text:JSON.stringify(result)}]});
 }catch(e){return ok({isError:true,content:[{type:'text',text:e instanceof z.ZodError?'Tool input validation failed':e instanceof Error?e.message:'Tool execution failed'}]});}
}
export async function workflowMcp<T>(db:D1Database,owner:string,name:string,args:unknown):Promise<T|null>{
 const response=await dispatchMcp({jsonrpc:'2.0',id:crypto.randomUUID(),method:'tools/call',params:{name,arguments:args}},db,owner) as {error?:{message:string};result?:{isError:boolean;content:{text:string}[]}};
 if(response.error)throw Error(response.error.message);if(response.result?.isError){if((name==='get_complaint'&&response.result.content[0]?.text.startsWith('Complaint not found'))||(['get_customer','get_transaction','get_account'].includes(name)&&response.result.content[0]?.text.startsWith('Linked record unavailable')))return null;throw Error(response.result.content[0]?.text||'MCP tool failed');}
 return JSON.parse(response.result!.content[0].text) as T;
}
export async function mcpHttp(request:Request,env:RuntimeEnv){
 const headers={'Content-Type':'application/json','Cache-Control':'no-store'};
 if(request.method!=='POST')return new Response('Method not allowed',{status:405,headers:{Allow:'POST'}});
 const origin=request.headers.get('origin');if(origin&&origin!==new URL(request.url).origin)return new Response('Origin refused',{status:403});
 if(!request.headers.get('content-type')?.includes('application/json'))return new Response('JSON required',{status:415});
 const text=await request.text();if(text.length>20000)return new Response('Request too large',{status:413});
 let input:unknown;try{input=JSON.parse(text);}catch{return Response.json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error'}},{status:400,headers});}
 if(!env.DB)return new Response('Database unavailable',{status:503});
 const user=request.headers.get('oai-authenticated-user-id');
 if((input as {method?:string})?.method==='tools/call'&&!user)return new Response('Authentication required',{status:401,headers});
 await seedDB(env.DB);if(user)await quota(env.DB,'mcp:'+user+':'+now().slice(0,10),300);
 const result=await dispatchMcp(input,env.DB,user?'mcp:'+user:null);
 return result?Response.json(result,{headers}):new Response(null,{status:202});
}
