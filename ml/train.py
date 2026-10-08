"""Reproducible chronological response-delay experiment. No outcome leakage."""
from pathlib import Path
import json, hashlib, datetime, time
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss)
ROOT=Path(__file__).resolve().parent
FIELDS=['product','sub_product','issue','sub_issue','submitted_via','company_key']
def metrics(y,p,t):
 q=p>=t
 return { 'accuracy':float(accuracy_score(y,q)), 'precision':float(precision_score(y,q,zero_division=0)), 'recall':float(recall_score(y,q,zero_division=0)), 'f1':float(f1_score(y,q,zero_division=0)), 'roc_auc':float(roc_auc_score(y,p)), 'average_precision':float(average_precision_score(y,p)), 'brier_score':float(brier_score_loss(y,p)), 'confusion_matrix':confusion_matrix(y,q,labels=[0,1]).tolist(), 'support':len(y), 'positive_support':int(sum(y)), 'positive_rate':float(np.mean(y)), 'threshold':float(t)}
def main():
 started=time.perf_counter(); data=ROOT/'data/cfpb-response-sample.jsonl';df=pd.read_json(data,lines=True,dtype=False).sort_values(['date_received','complaint_id']);df['date_received']=df.date_received.astype(str)
 df[FIELDS]=df[FIELDS].fillna('__missing__').astype(str)
 groups=[df[df.date_received<'2016-07-01'],df[(df.date_received>='2016-07-01')&(df.date_received<'2017-01-01')],df[df.date_received>='2017-01-01']]
 assert all(len(g)>500 for g in groups)
 assert set(groups[0].complaint_id).isdisjoint(groups[1].complaint_id) and set(groups[0].complaint_id).isdisjoint(groups[2].complaint_id) and set(groups[1].complaint_id).isdisjoint(groups[2].complaint_id)
 y=[(g.timely=='No').to_numpy().astype(int) for g in groups];assert all(sum(a)>=20 for a in y), [int(sum(a)) for a in y]
 encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=True);x=[encoder.fit_transform(groups[0][FIELDS])];x.extend(encoder.transform(g[FIELDS]) for g in groups[1:])
 baseline=DummyClassifier(strategy='prior').fit(x[0],y[0]); baseline_report=metrics(y[2],baseline.predict_proba(x[2])[:,1],.5)
 candidates=[]
 for c in [.1,1.,10.]:candidates.append((f'LogisticRegression C={c}',LogisticRegression(C=c,max_iter=1000,random_state=42)))
 candidates.append(('RandomForest depth=6',RandomForestClassifier(n_estimators=80,max_depth=6,min_samples_leaf=15,random_state=42,n_jobs=2)))
 experiments=[];trained=[]
 for name,model in candidates:
  model.fit(x[0],y[0]);p=model.predict_proba(x[1])[:,1]; thresholds=np.unique(np.concatenate(([.5],np.quantile(p,np.linspace(.05,.995,100)))))
  threshold=max(thresholds,key=lambda t:f1_score(y[1],p>=t,zero_division=0));m=metrics(y[1],p,threshold);experiments.append({'model':name,'validation':m});trained.append((name,model,threshold,m))
 # Choose by validation average precision; never use test data to select model/threshold.
 name,final,threshold,val=max(trained,key=lambda a:a[3]['average_precision']);p=final.predict_proba(x[2])[:,1];test=metrics(y[2],p,threshold)
 artifact={'version':'cfpb-delay-v2','target':'historical response delay (timely=No)','fields':FIELDS,'categories':[list(c) for c in encoder.categories_],'threshold':float(threshold),'algorithm':name,'training_data_sha256':hashlib.sha256(data.read_bytes()).hexdigest()}
 if isinstance(final,LogisticRegression):artifact.update(kind='logistic',coefficients=final.coef_[0].tolist(),intercept=float(final.intercept_[0]))
 else:
  artifact['kind']='forest';artifact['trees']=[]
  for estimator in final.estimators_:
   t=estimator.tree_;v=t.value[:,0,:];den=v.sum(axis=1);prob=np.divide(v[:,1],den,out=np.zeros_like(den),where=den!=0)
   artifact['trees'].append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'probability':prob.tolist()})
 unknown=np.mean([sum(str(r[f]) not in artifact['categories'][i] for i,f in enumerate(FIELDS))/len(FIELDS) for _,r in groups[2].iterrows()])
 errors=[]
 order=np.argsort(-np.abs(p-y[2]));test_rows=groups[2].to_dict('records')
 for i in order:
  if bool(p[i]>=threshold)!=bool(y[2][i]):errors.append({'record_id':str(test_rows[i]['complaint_id']),'features':{f:test_rows[i][f] for f in FIELDS},'actual_delay':bool(y[2][i]),'probability':float(p[i]),'predicted_delay':bool(p[i]>=threshold),'category':'ML classification error','improvement':'Collect current, representative complaint outcomes; compare calibrated models and investigate category drift.'})
  if len(errors)==12:break
 approved=test['positive_support']>=30 and test['roc_auc']>=.65 and test['precision']>test['positive_rate']
 report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model_version':artifact['version'],'dataset':json.loads((ROOT/'data/provenance.json').read_text()),'task':'Response-delay triage for historical US financial complaints; NOT fraud or refund entitlement','features':FIELDS,'split':{'method':'chronological, no refit on validation/test','train':{'rows':len(groups[0]),'positives':int(sum(y[0])),'start':str(groups[0].date_received.min()),'end':str(groups[0].date_received.max())},'validation':{'rows':len(groups[1]),'positives':int(sum(y[1])),'start':str(groups[1].date_received.min()),'end':str(groups[1].date_received.max())},'test':{'rows':len(groups[2]),'positives':int(sum(y[2])),'start':str(groups[2].date_received.min()),'end':str(groups[2].date_received.max())}},'baseline':{'algorithm':'Dummy prior, threshold 0.5','test':baseline_report},'experiments':experiments,'selected_model':name,'validation':val,'test':test,'test_unseen_category_fraction':float(unknown),'failure_cases':errors,'promotion':{'status':'shadow_only','statistical_gate_passed':approved,'reason':'Historical convenience sample and temporal/domain shift; no current deployment validation. Scores are reviewer context only and never authorize refunds, fraud labels or external actions.'},'training_seconds':time.perf_counter()-started,'selection':'Highest validation average precision; threshold maximizes validation F1; test evaluated once after selection.'}
 out=ROOT/'artifacts';out.mkdir(exist_ok=True);(out/'risk-model.json').write_text(json.dumps(artifact,separators=(',',':')));(out/'evaluation.json').write_text(json.dumps(report,indent=2));joblib.dump({'encoder':encoder,'model':final,'threshold':threshold,'fields':FIELDS},out/'risk-model.joblib')
 # Frozen parity vectors and public examples never include outcomes in the inference input.
 indexes=list(dict.fromkeys([int(np.argmax(p)),int(np.argmin(p)),*map(int,np.argsort(-p)[:4])]))
 examples=[{'id':f'CP-{j+1:03d}','source':'Historical CFPB public record; replay, not a current customer','features':{f:test_rows[i][f] for f in FIELDS}} for j,i in enumerate(indexes)]
 (out/'complaint-examples.json').write_text(json.dumps(examples,indent=2));(out/'parity.json').write_text(json.dumps([{'features':{f:r[f] for f in FIELDS},'probability':float(p[i])} for i,r in enumerate(test_rows[:50])],indent=2))
 print(json.dumps({'selected':name,'test':test,'promotion':report['promotion'],'training_seconds':report['training_seconds']},indent=2))
if __name__=='__main__':main()
