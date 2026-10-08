"""Verify retained data, held-out metrics and exported weights without refitting."""
import json, hashlib
import joblib
import numpy as np
import pandas as pd
from train import ROOT, FIELDS, metrics
artifact=json.loads((ROOT/'artifacts/risk-model.json').read_text())
report=json.loads((ROOT/'artifacts/evaluation.json').read_text())
raw=ROOT/'data/cfpb-response-sample.jsonl'
assert hashlib.sha256(raw.read_bytes()).hexdigest()==artifact['training_data_sha256']==report['dataset']['sha256']
assert not set(FIELDS)&{'timely','company_response','date_sent_to_company','complaint_id','date_received'}
df=pd.read_json(raw,lines=True,dtype=False).sort_values(['date_received','complaint_id']);df['date_received']=df.date_received.astype(str);df[FIELDS]=df[FIELDS].fillna('__missing__').astype(str)
assert not df.complaint_id.duplicated().any()
train=df[df.date_received<'2016-07-01'];val=df[(df.date_received>='2016-07-01')&(df.date_received<'2017-01-01')];test=df[df.date_received>='2017-01-01']
assert train.date_received.max()<val.date_received.min()<test.date_received.min()
assert (len(train),len(val),len(test))==(12000,4000,4000)
saved=joblib.load(ROOT/'artifacts/risk-model.joblib')
x=saved['encoder'].transform(test[FIELDS]);p=saved['model'].predict_proba(x)[:,1]
actual=metrics((test.timely=='No').astype(int).to_numpy(),p,saved['threshold'])
for key in ['accuracy','precision','recall','f1','roc_auc','average_precision','brier_score']:
    assert abs(actual[key]-report['test'][key])<1e-12,key
assert actual['confusion_matrix']==report['test']['confusion_matrix']
for c in json.loads((ROOT/'artifacts/parity.json').read_text()):
    z=saved['encoder'].transform(pd.DataFrame([c['features']])[FIELDS]);reference=saved['model'].predict_proba(z)[0,1]
    dense=z.toarray()[0];portable=1/(1+np.exp(-(artifact['intercept']+np.dot(dense,artifact['coefficients']))))
    assert abs(reference-portable)<1e-12 and abs(reference-c['probability'])<1e-12
result={'verified_at':pd.Timestamp.now(tz='UTC').isoformat(),'dataset_hash_verified':True,'temporal_splits_verified':True,'artifact_metrics_reproduced_without_training':True,'raw_prediction_parity_vectors':50,'test':actual}
(ROOT.parent/'verification/ml.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
