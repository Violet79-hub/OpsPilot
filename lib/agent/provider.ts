import { z } from 'zod';
import type { RuntimeEnv,State } from './types';
export type Usage=NonNullable<State['usage']>;
export const emptyUsage=():Usage=>({input_tokens:0,output_tokens:0,embedding_tokens:0});
async function call(env:RuntimeEnv,path:string,payload:unknown){
 if(!env.OPENAI_API_KEY)throw new Error('MODEL_NOT_CONFIGURED: An owner-provided OpenAI API key is required. No recorded answer was substituted.');
 const response=await fetch('https://api.openai.com/v1/'+path,{method:'POST',headers:{Authorization:`Bearer ${env.OPENAI_API_KEY}`,'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(25000)});
 if(!response.ok)throw new Error(`Model provider returned HTTP ${response.status}. Check the server key, quota and model access.`);
 return response.json() as Promise<Record<string,unknown>>;
}
export async function structured<T>(env:RuntimeEnv,name:string,schema:z.ZodType<T>,jsonSchema:unknown,system:string,input:unknown,usage:Usage):Promise<T>{
 const data=await call(env,'chat/completions',{model:env.OPENAI_MODEL||'gpt-4o-mini',temperature:0,max_tokens:1800,messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(input)}],response_format:{type:'json_schema',json_schema:{name,strict:true,schema:jsonSchema}}});
 const body=z.object({choices:z.array(z.object({message:z.object({content:z.string().nullable(),refusal:z.string().nullable().optional()})})),usage:z.object({prompt_tokens:z.number(),completion_tokens:z.number()})}).parse(data);
 usage.input_tokens+=body.usage.prompt_tokens;usage.output_tokens+=body.usage.completion_tokens;
 if(!body.choices[0]?.message.content)throw new Error('Provider refused or returned no structured answer.');
 return schema.parse(JSON.parse(body.choices[0].message.content));
}
export async function embeddings(env:RuntimeEnv,input:string[],usage:Usage):Promise<number[][]>{
 const data=await call(env,'embeddings',{model:'text-embedding-3-small',dimensions:512,input});
 const body=z.object({data:z.array(z.object({index:z.number(),embedding:z.array(z.number()).length(512)})),usage:z.object({total_tokens:z.number()})}).parse(data);
 usage.embedding_tokens+=body.usage.total_tokens;
 if(body.data.length!==input.length)throw new Error('Incomplete embedding response');
 return body.data.sort((a,b)=>a.index-b.index).map(x=>x.embedding);
}
export const planJSON={type:'object',additionalProperties:false,properties:{complaint_id:{type:['string','null']},tool_names:{type:'array',items:{type:'string',enum:['get_order','get_customer','get_support_ticket','calculate_refund','get_complaint','predict_response_delay']}},intent:{type:'string',enum:['refund','privacy','unsupported','complaint']},order_id:{type:['string','null']},customer_id:{type:['string','null']},ticket_id:{type:['string','null']},query:{type:'string'},steps:{type:'array',items:{type:'string'}}},required:['complaint_id','tool_names','intent','order_id','customer_id','ticket_id','query','steps']};
export const answerJSON={type:'object',additionalProperties:false,properties:{decision:{type:'string',enum:['approve','deny','escalate','warranty','insufficient_evidence']},amount:{type:'number'},explanation:{type:'string'},customer_reply:{type:'string'},citations:{type:'array',items:{type:'string'}}},required:['decision','amount','explanation','customer_reply','citations']};
