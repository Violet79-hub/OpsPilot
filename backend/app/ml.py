"""Portable scorer for the actual trained artifact, shared with deployed Workers."""
from pathlib import Path
import json
import math
from pydantic import BaseModel, ConfigDict, Field
ROOT=Path(__file__).resolve().parents[2]
MODEL=json.loads((ROOT/'ml/artifacts/risk-model.json').read_text())
class ComplaintFeatures(BaseModel):
    model_config=ConfigDict(extra='forbid')
    product:str=Field(min_length=1,max_length=180)
    sub_product:str=Field(min_length=1,max_length=180)
    issue:str=Field(min_length=1,max_length=180)
    sub_issue:str=Field(min_length=1,max_length=180)
    submitted_via:str=Field(min_length=1,max_length=60)
    company_key:str=Field(pattern=r'^[0-9a-f]{16}$')
def predict_response_delay(features:dict):
    features=ComplaintFeatures(**features).model_dump()
    unknown=[f for i,f in enumerate(MODEL['fields']) if features[f] not in MODEL['categories'][i]]
    if 'product' in unknown or len(unknown)>2:
        return {'status':'abstained','risk_probability':None,'model_version':MODEL['version'],'unknown_fields':unknown,'priority':'manual_review','shadow_only':True}
    x=[int(features[f]==c) for i,f in enumerate(MODEL['fields']) for c in MODEL['categories'][i]]
    if MODEL['kind']=='logistic':
        score=MODEL['intercept']+sum(v*w for v,w in zip(x,MODEL['coefficients']))
        p=1/(1+math.exp(-max(-700,min(700,score))))
    else:
        probabilities=[]
        for t in MODEL['trees']:
            node=0
            while t['left'][node]!=-1:
                node=t['left'][node] if x[t['feature'][node]]<=t['threshold'][node] else t['right'][node]
            probabilities.append(t['probability'][node])
        p=sum(probabilities)/len(probabilities)
    return {'status':'scored','risk_probability':p,'model_version':MODEL['version'],'threshold':MODEL['threshold'],'priority':'suggested_priority_review' if p>=MODEL['threshold'] else 'standard_review','shadow_only':True,'unknown_fields':unknown,'target':'historical response delay, not fraud or refund entitlement'}
