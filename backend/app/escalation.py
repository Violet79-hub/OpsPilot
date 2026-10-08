"""Inference using the exported synthetic-trained forest, without pickle loading."""
from pathlib import Path
import json
from pydantic import BaseModel,Field,ConfigDict
ROOT=Path(__file__).resolve().parents[2];MODEL=json.loads((ROOT/'ml/escalation/model.json').read_text())
class EscalationFeatures(BaseModel):
 model_config=ConfigDict(extra='forbid')
 amount:float=Field(ge=0,le=1000000)
 transaction_age_days:float=Field(ge=0,le=36500)
 gold_customer:int=Field(ge=0,le=1)
 previous_complaints:int=Field(ge=0,le=100)
 resolution_attempts:int=Field(ge=0,le=100)
 vulnerable:int=Field(ge=0,le=1)
 fraud_flag:int=Field(ge=0,le=1)
 evidence_completeness:float=Field(ge=0,le=1)
 previous_escalations:int=Field(ge=0,le=100)
 web_channel:int=Field(ge=0,le=1)
def score_escalation(features):
 values=EscalationFeatures(**features).model_dump();x=[values[k] for k in MODEL['fields']];total=0
 for tree in MODEL['trees']:
  n=0
  while tree['left'][n]!=-1:n=tree['left'][n] if x[tree['feature'][n]]<=tree['threshold'][n] else tree['right'][n]
  total+=tree['probability'][n]
 probability=total/len(MODEL['trees'])
 return {'risk_probability':probability,'risk_level':'HIGH' if probability>=.65 else 'MEDIUM' if probability>=MODEL['threshold'] else 'LOW','model_version':MODEL['version'],'synthetic_training':True,'shadow_only':True,'features_used':values}
