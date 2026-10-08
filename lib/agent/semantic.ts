import artifact from './semantic-artifact.json';
const dimensions=artifact.dimensions;
const vocab=artifact.vocab as Record<string,number>;
let weights:Int8Array|null=null;
function table(){if(!weights){const s=atob(artifact.weights);weights=new Int8Array(s.length);for(let i=0;i<s.length;i++)weights[i]=s.charCodeAt(i);}return weights;}
/** BERT uncased WordPiece, no CLS/SEP (StaticEmbedding pools content tokens). */
export function semanticTokens(text:string):number[]{
 const normalized=text.replace(/[\u0000\ufffd\p{Cc}\p{Cf}]/gu,c=>/\s/u.test(c)?' ':'').toLowerCase().normalize('NFD').replace(/\p{Mn}/gu,'').replace(/([\p{Script=Han}])/gu,' $1 ');
 const pieces=normalized.match(/[\p{P}\x21-\x2f\x3a-\x40\x5b-\x60\x7b-\x7e]|[^\s\p{P}\x21-\x2f\x3a-\x40\x5b-\x60\x7b-\x7e]+/gu)||[];
 const ids:number[]=[];
 for(const word of pieces){if(word.length>100){ids.push(vocab['[UNK]']);continue;}let start=0;const sub:number[]=[];while(start<word.length){let end=word.length,id: number|undefined;while(end>start){id=vocab[(start?'##':'')+word.slice(start,end)];if(id!==undefined)break;end--;}if(id===undefined){sub.length=0;sub.push(vocab['[UNK]']);break;}sub.push(id);start=end;}ids.push(...sub);}
 return ids;
}
export function localEmbedding(text:string):number[]{const ids=semanticTokens(text),out=new Array<number>(dimensions).fill(0),w=table();for(const id of ids){const scale=artifact.scales[id];for(let d=0;d<dimensions;d++)out[d]+=w[id*dimensions+d]*scale;}const norm=Math.sqrt(out.reduce((a,x)=>a+x*x,0));return norm?out.map(x=>x/norm):out;}
export const semanticModel={name:artifact.model,revision:artifact.revision,dimensions,quantization:artifact.quantization,language:'English',provider_calls:0};
export function semanticRank<T extends {id:string;body:string;name:string}>(docs:T[],query:string){const q=localEmbedding(query);return docs.map(doc=>{const chunks:string[]=[];for(let i=0;i<doc.body.length;i+=1400){chunks.push(doc.body.slice(i,i+1600));if(i+1600>=doc.body.length)break;}const ranked=chunks.map((text,index)=>{const v=localEmbedding(doc.name+'\n'+text);return {id:doc.id+':chunk:'+index,section:doc.name.match(/§([0-9.]+)/)?.[1]||'Full policy',start:index*1400,end:index*1400+text.length,text,score:q.reduce((s,x,i)=>s+x*v[i],0)};}).sort((a,b)=>b.score-a.score);return {...doc,chunks:ranked.slice(0,2),embedding_status:'Local vectors computed on demand',document_version:'demo-1',body:ranked.slice(0,2).map(c=>c.text).join('\n\n[…]\n\n'),score:ranked[0]?.score||0};}).sort((a,b)=>b.score-a.score).slice(0,6);}
