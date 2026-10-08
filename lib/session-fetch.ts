// Serialize anonymous cookie creation before concurrent API requests.
let ready:Promise<void>|null=null;
async function establish(){const r=await fetch('/api/health',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Unable to connect to the case service. Please retry.');}
export async function sessionFetch(input:string,init:RequestInit={}){if(!ready)ready=establish().catch(e=>{ready=null;throw e;});await ready;return fetch(input,{...init,credentials:'same-origin',signal:init.signal||AbortSignal.timeout(30000)});}
