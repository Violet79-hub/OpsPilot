import {z} from 'zod';
import {getRecord,now,id} from './store';
import type {ComplaintFeatures} from './ml';
export type ComplaintRecord={id:string;features:ComplaintFeatures;summary?:string;source?:string};
export type CaseFile={revision:number;stage:'investigating'|'waiting_for_information'|'ready_for_review';evidence:{id:string;name:string;text:string;created:string}[];history:{at:string;action:string;note:string;revision:number}[]};
export async function complaintRecord(db:D1Database,owner:string,key:string){return await getRecord<ComplaintRecord>(db,key,'complaints:'+owner)||await getRecord<ComplaintRecord>(db,key,'complaints');}
const fileKey=(owner:string,key:string)=>'casefile:'+owner+':'+key;
export async function caseFile(db:D1Database,owner:string,key:string):Promise<CaseFile>{return await getRecord<CaseFile>(db,fileKey(owner,key),'casefile:'+owner)||{revision:0,stage:'investigating',evidence:[],history:[]};}
export const caseChange=z.object({revision:z.number().int().min(0),action:z.enum(['add_evidence','request_information','resume']),note:z.string().trim().min(5).max(2000),name:z.string().trim().max(120).optional(),text:z.string().trim().max(12000).optional()}).strict();
export async function changeCase(db:D1Database,owner:string,key:string,input:z.infer<typeof caseChange>){
 const record=await complaintRecord(db,owner,key);if(!record)return {error:'Case not found',status:404};
 const previous=await caseFile(db,owner,key);if(previous.revision!==input.revision)return {error:'This case changed. Reload it before saving.',status:409};
 const latestRequest=previous.history.filter(h=>h.action==='request_information').at(-1);if(input.action==='resume'&&latestRequest&&!previous.history.some(h=>h.action==='add_evidence'&&h.revision>latestRequest.revision))return {error:'Attach the requested information before resuming.',status:409};
 if(input.action==='add_evidence'&&(!input.name||!input.text||input.text.length<10))return {error:'Evidence needs a title and at least 10 characters.',status:400};
 if(previous.evidence.length>=20&&input.action==='add_evidence')return {error:'Maximum 20 evidence records per case.',status:429};
 const updated:CaseFile={...previous,revision:previous.revision+1,stage:input.action==='request_information'?'waiting_for_information':input.action==='resume'?'ready_for_review':previous.stage,evidence:input.action==='add_evidence'?[...previous.evidence,{id:id(),name:input.name!,text:input.text!,created:now()}]:previous.evidence,history:[...previous.history,{at:now(),action:input.action,note:input.note,revision:previous.revision+1}]};
 const keyId=fileKey(owner,key);await db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind(keyId,'casefile:'+owner,JSON.stringify({revision:0,stage:'investigating',evidence:[],history:[]})).run();
 const result=await db.prepare("UPDATE records SET body=? WHERE id=? AND kind=? AND json_extract(body,'$.revision')=?").bind(JSON.stringify(updated),keyId,'casefile:'+owner,input.revision).run();
 return result.meta.changes?{data:updated,status:200}:{error:'Concurrent case update. Reload before saving.',status:409};
}
