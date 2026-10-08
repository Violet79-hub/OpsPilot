import financialRecords from './financial-records.json';
import financialPolicies from './financial-policies.json';
import demoComplaints from './demo-complaints.json';
import {complaintExamples} from './ml';
import seed from './seed.json';
import type { Document, Run } from './types';
export const now=()=>new Date().toISOString();
export const id=()=>crypto.randomUUID();
export async function seedDB(db:D1Database){
 const exists=await db.prepare("SELECT id FROM records WHERE id='seed:v2'").first();if(exists){await seedModel(db);return;}
 const statements=[];
 for(const kind of ['customers','orders','support_tickets'] as const)for(const record of seed[kind])statements.push(db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind(record.id,kind,JSON.stringify(record)));
 for(const doc of seed.documents)statements.push(db.prepare('INSERT OR IGNORE INTO documents(id,owner,name,body,trusted,created) VALUES(?,?,?,?,1,?)').bind(doc.id,'global',doc.name,doc.text,now()));
 statements.push(db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind('seed:v2','meta','{}'));
 await db.batch(statements);await seedModel(db);
}
export async function getRecord<T>(db:D1Database,key:string|null,kind:string):Promise<T|null>{if(!key)return null;const r=await db.prepare('SELECT body FROM records WHERE id=? AND kind=?').bind(key,kind).first<{body:string}>();return r?JSON.parse(r.body):null;}
export async function getRun(db:D1Database,key:string,owner:string){return db.prepare('SELECT * FROM runs WHERE id=? AND owner=?').bind(key,owner).first<Run>();}
export async function getDocs(db:D1Database,owner:string){return (await db.prepare("SELECT * FROM documents WHERE owner='global' OR owner=? ORDER BY trusted DESC,created DESC LIMIT 50").bind(owner).all<Document>()).results;}
export async function event(db:D1Database,runId:string,node:string,body:unknown){await db.prepare('INSERT INTO events(run_id,node,body,created) VALUES(?,?,?,?)').bind(runId,node,JSON.stringify(body),now()).run();}
export async function quota(db:D1Database,key:string,limit:number){const result=await db.prepare('INSERT INTO quotas(id,count) VALUES(?,1) ON CONFLICT(id) DO UPDATE SET count=count+1 WHERE count<? RETURNING count').bind(key,limit).first();if(!result)throw new Error('Daily execution limit reached. Please try again tomorrow.');}

async function seedModel(db:D1Database){
 if(!await db.prepare("SELECT id FROM records WHERE id='seed:demo:v2'").first()){await db.batch([...demoComplaints.map(r=>db.prepare("INSERT INTO records(id,kind,body) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body WHERE records.kind='complaints' AND json_extract(records.body,'$.synthetic')=1").bind(r.id,'complaints',JSON.stringify(r))),db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind('seed:demo:v2','meta','{}')]);}

 if(!await db.prepare("SELECT id FROM records WHERE id='seed:financial:v1'").first()){const statements=[];for(const [kind,rows] of Object.entries(financialRecords))for(const row of rows)statements.push(db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind(row.id,kind,JSON.stringify(row)));for(const doc of financialPolicies)statements.push(db.prepare('INSERT OR IGNORE INTO documents(id,owner,name,body,trusted,created) VALUES(?,?,?,?,1,?)').bind(doc.id,'global',doc.name,doc.text,now()));statements.push(db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind('seed:financial:v1','meta','{}'));await db.batch(statements);}
 if(await db.prepare("SELECT id FROM records WHERE id='seed:ml:v1'").first())return;
 const statements=complaintExamples.map(r=>db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind(r.id,'complaints',JSON.stringify(r)));
 statements.push(db.prepare('INSERT OR IGNORE INTO documents(id,owner,name,body,trusted,created) VALUES(?,?,?,?,1,?)').bind('complaint_triage','global','Complaint Triage — Demo Internal Policy','This synthetic internal demonstration policy is not a legal or regulatory rule. Financial complaints require human review. Use the historical CFPB response-delay model only for supported financial complaint categories. The model predicts timely=No outcomes, not fraud, refund eligibility or real escalation. Historical scores are shadow reviewer context only: a score above the validation-selected threshold suggests priority review, never an automatic financial decision. Unknown domains require manual review. Do not send payments or external messages. Cite this policy and retain model version, score, unknown features and limitations.',now()));
 statements.push(db.prepare('INSERT OR IGNORE INTO records(id,kind,body) VALUES(?,?,?)').bind('seed:ml:v1','meta','{}'));await db.batch(statements);
}
