"""Synthetic escalation research experiment; NOT real-world risk validation."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,average_precision_score,confusion_matrix,roc_curve
import joblib
root=Path(__file__).parent;rng=np.random.default_rng(8128);n=2000
fields=['amount','transaction_age_days','gold_customer','previous_complaints','resolution_attempts','vulnerable','fraud_flag','evidence_completeness','previous_escalations','web_channel']
x=np.column_stack([rng.uniform(10,3000,n),rng.integers(0,100,n),rng.binomial(1,.3,n),rng.poisson(1.2,n),rng.integers(0,5,n),rng.binomial(1,.12,n),rng.binomial(1,.1,n),rng.uniform(0,1,n),rng.poisson(.3,n),rng.binomial(1,.7,n)])
p=.05+.55*(x[:,5]>0)+.6*(x[:,6]>0)+.35*((x[:,0]>1000)&(x[:,7]<.6))+.25*((x[:,3]>=3)&(x[:,4]>=2))+.15*(x[:,8]>0)
y=rng.binomial(1,np.clip(p,.02,.95));indices=np.arange(n);train,rest=train_test_split(indices,test_size=.4,stratify=y,random_state=17);val,test=train_test_split(rest,test_size=.5,stratify=y[rest],random_state=18)
rows=[dict(row_id=int(i),split='train' if i in train else 'validation' if i in val else 'test',**dict(zip(fields,x[i].tolist())),escalated=int(y[i])) for i in indices];raw=json.dumps(rows,separators=(',',':'));(root/'dataset.json').write_text(raw)
models={'Logistic regression':make_pipeline(StandardScaler(),LogisticRegression(max_iter=500,random_state=17)),'Random forest':RandomForestClassifier(n_estimators=60,max_depth=6,min_samples_leaf=8,random_state=17,n_jobs=1)}
for m in models.values():m.fit(x[train],y[train])
validation={k:float(average_precision_score(y[val],m.predict_proba(x[val])[:,1])) for k,m in models.items()};selected=max(validation,key=validation.get);model=models[selected]
thresholds=np.linspace(.15,.75,25);threshold=float(max(thresholds,key=lambda t:f1_score(y[val],model.predict_proba(x[val])[:,1]>=t)))
def metrics(m):
 probs=m.predict_proba(x[test])[:,1];pred=probs>=threshold;fpr,tpr,_=roc_curve(y[test],probs)
 return dict(accuracy=float(accuracy_score(y[test],pred)),precision=float(precision_score(y[test],pred,zero_division=0)),recall=float(recall_score(y[test],pred,zero_division=0)),f1=float(f1_score(y[test],pred)),roc_auc=float(roc_auc_score(y[test],probs)),average_precision=float(average_precision_score(y[test],probs)),confusion_matrix=confusion_matrix(y[test],pred).tolist(),roc=[dict(fpr=float(a),tpr=float(b)) for a,b in zip(fpr[::5],tpr[::5])])
artifact=dict(version='synthetic-escalation-v1',fields=fields,threshold=threshold,model_type=selected,training_data_sha256=hashlib.sha256(raw.encode()).hexdigest())
if selected=='Random forest':
 artifact['trees']=[]
 for estimator in model.estimators_:
  t=estimator.tree_;counts=t.value[:,0,:];artifact['trees'].append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),feature=t.feature.tolist(),threshold=t.threshold.tolist(),probability=(counts[:,1]/counts.sum(axis=1)).tolist()))
 importance=model.feature_importances_
else:
 scale,lr=model.steps[0][1],model.steps[1][1];artifact.update(mean=scale.mean_.tolist(),scale=scale.scale_.tolist(),coefficients=lr.coef_[0].tolist(),intercept=float(lr.intercept_[0]));importance=np.abs(lr.coef_[0])
(root/'model.json').write_text(json.dumps(artifact,separators=(',',':')));joblib.dump(model,root/'model.joblib');probs=model.predict_proba(x[test])[:,1]
report=dict(model_version=artifact['version'],trained_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected_model=selected,dataset_size=n,dataset_sha256=artifact['training_data_sha256'],synthetic=True,scope='Labels are sampled from an explicitly programmed synthetic mechanism. Metrics measure recovery of that mechanism, not actual customer escalation. Shadow-only; no financial decision may use this probability as authority.',split={name:dict(rows=len(ix),positive=int(y[ix].sum())) for name,ix in [('train',train),('validation',val),('test',test)]},selection='Validation average precision chooses the model; validation F1 chooses the threshold; test used once for reporting.',validation_average_precision=validation,threshold=threshold,baseline=metrics(models['Logistic regression']),test=metrics(model),feature_importance=dict(zip(fields,map(float,importance))),failure_cases=[dict(row_id=int(i),actual=int(y[i]),probability=float(prob),features=dict(zip(fields,x[i].tolist()))) for i,prob in zip(test,probs) if (prob>=threshold)!=bool(y[i])][:12])
(root/'evaluation.json').write_text(json.dumps(report,indent=2));(root/'parity.json').write_text(json.dumps([dict(features=dict(zip(fields,x[i].tolist())),probability=float(model.predict_proba(x[i:i+1])[:,1][0])) for i in test[:30]]));print(json.dumps({'selected':selected,'validation':validation,'test':report['test'],'threshold':threshold}))
