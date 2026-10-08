import { z } from 'zod';
import model from '../../ml/artifacts/risk-model.json';
import report from '../../ml/artifacts/evaluation.json';
import examples from '../../ml/artifacts/complaint-examples.json';
export const complaintSchema=z.object({product:z.string().min(1).max(180),sub_product:z.string().min(1).max(180),issue:z.string().min(1).max(180),sub_issue:z.string().min(1).max(180),submitted_via:z.string().min(1).max(60),company_key:z.string().regex(/^[0-9a-f]{16}$/)}).strict();
export type ComplaintFeatures=z.infer<typeof complaintSchema>;
type Artifact={kind:string;version:string;algorithm:string;fields:string[];categories:string[][];threshold:number;intercept?:number;coefficients?:number[];trees?:{left:number[];right:number[];feature:number[];threshold:number[];probability:number[]}[]};
const artifact=model as Artifact;
export const mlReport=report;
export const complaintExamples=examples;
export function predictResponseDelay(input:unknown){
 const features=complaintSchema.parse(input);const known:string[]=[],unknown:string[]=[];const encoded:number[]=[];
 artifact.fields.forEach((field,i)=>{const value=features[field as keyof ComplaintFeatures];(artifact.categories[i].includes(value)?known:unknown).push(field);artifact.categories[i].forEach(c=>encoded.push(c===value?1:0));});
 if(unknown.includes('product')||unknown.length>2)return {status:'abstained' as const,model_version:artifact.version,reason:'Out-of-domain categories. This historical financial-complaint model cannot score retail orders or unrelated requests.',unknown_fields:unknown,risk_probability:null,priority:'manual_review',shadow_only:true};
 let probability:number;
 if(artifact.kind==='logistic'){const score=artifact.intercept!+encoded.reduce((s,v,i)=>s+v*artifact.coefficients![i],0);probability=1/(1+Math.exp(-Math.max(-700,Math.min(700,score))));}
 else {const trees=artifact.trees!;probability=trees.reduce((sum,t)=>{let node=0;while(t.left[node]!==-1)node=encoded[t.feature[node]]<=t.threshold[node]?t.left[node]:t.right[node];return sum+t.probability[node];},0)/trees.length;}
 return {status:'scored' as const,risk_probability:probability,priority:probability>=artifact.threshold?'suggested_priority_review':'standard_review',threshold:artifact.threshold,model_version:artifact.version,algorithm:artifact.algorithm,unknown_fields:unknown,shadow_only:true,target:'historical timely=No; not fraud or actual escalation',limitation:'Historical convenience sample; probability is not calibrated for current customers. Reviewer context only.'};
}
