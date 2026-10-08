import json
from pathlib import Path
from app.ml import predict_response_delay
ROOT=Path(__file__).resolve().parents[2]
def test_portable_model_matches_training_predictions():
    cases=json.loads((ROOT/'ml/artifacts/parity.json').read_text())
    for c in cases:
        result=predict_response_delay(c['features'])
        if result['status']=='scored':
            assert abs(result['risk_probability']-c['probability'])<1e-12
        else:
            assert result['status']=='abstained' and result['risk_probability'] is None

def test_ml_api_rejects_outcome_and_abstains(client):
    example=json.loads((ROOT/'ml/artifacts/complaint-examples.json').read_text())[0]['features']
    assert client.post('/ml/predict',json=example).json()['status']=='scored'
    assert client.post('/ml/predict',json={**example,'timely':'No'}).status_code==422
    assert client.post('/ml/predict',json={**example,'product':'Retail shoes'}).json()['status']=='abstained'
    report=client.get('/ml/evaluation').json()
    assert report['split']['test']['rows']==4000
    assert report['promotion']['status']=='shadow_only'
