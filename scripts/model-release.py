"""Reproducible local model registry: validate, package, atomically activate and rollback.
Activation here is a local artifact pointer. Publishing the Site is a separate operation.
"""
import argparse,datetime,hashlib,json,os,shutil,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(directory):
    model=json.loads((directory/'risk-model.json').read_text());report=json.loads((directory/'evaluation.json').read_text())
    assert model['version']==report['model_version'],'Model/report version mismatch'
    assert model['training_data_sha256']==report['dataset']['sha256'],'Dataset lineage mismatch'
    assert 0<model['threshold']<1,'Invalid inference threshold'
    assert report['promotion']['status']=='shadow_only','Unreviewed autonomous deployment forbidden'
    assert report['test']['roc_auc']>=.65 and report['test']['average_precision']>2*report['test']['positive_rate'],'Shadow research quality gate failed'
    assert report['test']['positive_support']>=30,'Insufficient positive test support'
    assert report['split']['train']['end']<report['split']['validation']['start']<report['split']['test']['start'],'Temporal leakage'
    assert len(model['coefficients'])==sum(map(len,model['categories'])),'Artifact dimensions mismatch'
    return model,report

def package(directory,registry,tag):
    model,report=validate(directory);target=registry/tag;target.mkdir(parents=True,exist_ok=False)
    names=['risk-model.json','evaluation.json','risk-model.joblib','parity.json']
    for name in names:shutil.copy2(directory/name,target/name)
    manifest={'release':tag,'model_version':model['version'],'dataset_sha256':model['training_data_sha256'],'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'shadow_only','files':{name:sha(target/name) for name in names}}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2));return target,manifest

def activate(registry,tag):
    directory=registry/tag;manifest=json.loads((directory/'manifest.json').read_text())
    for name,digest in manifest['files'].items():assert sha(directory/name)==digest,'Artifact integrity check failed'
    validate(directory)
    current=registry/'active.json';previous=json.loads(current.read_text()) if current.exists() else None
    new={'release':tag,'previous':previous['release'] if previous else None,'manifest_sha256':sha(directory/'manifest.json')}
    temp=registry/'active.tmp';temp.write_text(json.dumps(new));os.replace(temp,current);return new

def run():
    source=ROOT/'ml/artifacts';validate(source)
    # A disposable registry proves pointer changes and rollback without changing production.
    with tempfile.TemporaryDirectory(prefix='opspilot-registry-') as tmp:
        registry=Path(tmp);_,first=package(source,registry,'baseline-package');activate(registry,'baseline-package')
        _,second=package(source,registry,'candidate-package');activate(registry,'candidate-package');rolled=activate(registry,'baseline-package');assert rolled['release']=='baseline-package'
        corrupt=registry/'candidate-package/risk-model.json';corrupt.write_text('{}')
        rejected=False
        try:activate(registry,'candidate-package')
        except (AssertionError,KeyError):rejected=True
        assert rejected and json.loads((registry/'active.json').read_text())['release']=='baseline-package'
    public=ROOT/'public/releases';public.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        target,manifest=package(source,Path(tmp),'cfpb-delay-v2')
        with tarfile.open(public/'cfpb-delay-v2.tar.gz','w:gz') as tar:tar.add(target,arcname=target.name)
    report={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifact_version':'cfpb-delay-v2','quality_gate':'passed for shadow use only','integrity_gate':'passed','corrupt_candidate':'rejected; previous pointer preserved','rollback_drill':'passed in disposable local registry; same model in two release packages','production_rollback_tested':False,'archive_sha256':sha(public/'cfpb-delay-v2.tar.gz'),'manifest':manifest}
    (ROOT/'verification/model-release.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':run()
