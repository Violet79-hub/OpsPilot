"""Derive recruiter-facing numbers only from saved regression executions."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r=json.loads((root/'verification/runtime.json').read_text());f=json.loads((root/'verification/financial.json').read_text());s=json.loads((root/'verification/semantic.json').read_text())
suites=[]
for name,rows in [('Legacy refund regression',r['golden']['results']),('Financial complaint regression',f['results'])]:
 def rate(key):return sum(bool(x.get('checks',{}).get(key)) for x in rows)/len(rows)
 suites.append({'name':name,'cases':len(rows),'passed':sum(x['passed'] for x in rows),'decision':rate('decision'),'citations':rate('sources'),'tool_coverage':rate('tools'),'mean_latency_ms':round(sum(x.get('latency_ms',0) for x in rows)/len(rows),1),'failed':[{'case_id':x['case_id'],'checks':x.get('checks',{}),'error':x.get('error')} for x in rows if not x['passed']]})
report={'verified_at':r['verified_at'],'scope':'Measured local D1/LangGraph regression executions, not production traffic or LLM quality. Citation score checks required source IDs; tool score checks expected tool coverage, not autonomous tool-selection accuracy.','suites':suites,'retrieval':{'recall':s['semantic']['recall'],'mrr':s['semantic']['mrr'],'cases':s['semantic']['case_count'],'failed':[{'query':x['query'],'expected':x['relevant'],'retrieved':x['retrieved']} for x in s['semantic']['results'] if not x['passed']]},'provider_cost':'No provider calls in these local-mode tests. Hosting costs excluded; live provider cost is not measured.'}
(root/'lib/agent/benchmark-summary.json').write_text(json.dumps(report,indent=2));print('Benchmark summary derived from actual regression reports')
