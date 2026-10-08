import hashlib,json
from pathlib import Path
import numpy as np,joblib
from sklearn.metrics import f1_score,roc_auc_score,confusion_matrix
p=Path(__file__).parent;raw=(p/'dataset.json').read_bytes();rows=json.loads(raw);report=json.loads((p/'evaluation.json').read_text());artifact=json.loads((p/'model.json').read_text());assert hashlib.sha256(raw).hexdigest()==report['dataset_sha256']==artifact['training_data_sha256'];assert len(rows)==2000 and len({r['row_id'] for r in rows})==2000
for name,expected in report['split'].items():assert sum(r['split']==name for r in rows)==expected['rows']
model=joblib.load(p/'model.joblib');test=[r for r in rows if r['split']=='test'];x=np.array([[r[k] for k in artifact['fields']] for r in test]);y=np.array([r['escalated'] for r in test]);probs=model.predict_proba(x)[:,1];pred=probs>=report['threshold'];assert abs(f1_score(y,pred)-report['test']['f1'])<1e-12;assert abs(roc_auc_score(y,probs)-report['test']['roc_auc'])<1e-12;assert confusion_matrix(y,pred).tolist()==report['test']['confusion_matrix'];print('Synthetic dataset hash, disjoint row IDs, saved artifact and held-out metrics verified')
