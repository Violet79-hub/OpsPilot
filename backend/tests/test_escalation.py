import json
from pathlib import Path
import pytest
from app.escalation import score_escalation
ROOT=Path(__file__).resolve().parents[2]
def test_forest_matches_sklearn_reference():
 for row in json.loads((ROOT/'ml/escalation/parity.json').read_text()):
  result=score_escalation(row['features']);assert abs(result['risk_probability']-row['probability'])<1e-9;assert result['synthetic_training'] and result['shadow_only']
def test_outcome_field_rejected():
 row=json.loads((ROOT/'ml/escalation/parity.json').read_text())[0]['features']
 with pytest.raises(ValueError):score_escalation({**row,'escalated':1})
