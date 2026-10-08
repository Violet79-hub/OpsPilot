import asyncio,json,sys,httpx
def local_client(headers=None,timeout=None,auth=None):
    return httpx.AsyncClient(headers=headers,timeout=timeout,auth=auth,trust_env=False)
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
async def main():
    async with streamablehttp_client(sys.argv[1],headers={'oai-authenticated-user-id':'test-platform-user'},httpx_client_factory=local_client) as (read,write,_):
        async with ClientSession(read,write) as client:
            await client.initialize();tools=await client.list_tools();names=[t.name for t in tools.tools]
            assert set(names)=={'get_complaint','predict_response_delay','search_company_policy','get_model_card','get_customer','get_transaction','get_account','predict_escalation_risk'}
            record=await client.call_tool('get_complaint',{'id':'CP-001'});assert not record.isError
            features=json.loads(record.content[0].text)['features'];prediction=await client.call_tool('predict_response_delay',features);assert not prediction.isError
            assert json.loads(prediction.content[0].text)['status']=='scored'
            customer=await client.call_tool('get_customer',{'case_id':'CP-101'});assert json.loads(customer.content[0].text)['name']=='Emma Chen'
            risk=await client.call_tool('predict_escalation_risk',{'case_id':'CP-101'});assert json.loads(risk.content[0].text)['synthetic_training'] is True
            policy=await client.call_tool('search_company_policy',{'query':'financial complaint human review'});assert not policy.isError
            assert any(d['id']=='complaint_triage' for d in json.loads(policy.content[0].text))
            print(json.dumps({'official_python_sdk':True,'transport':'streamable HTTP','tools':names,'record_prediction_policy':'passed','identity':'local test header; production identity supplied by Sites'}))
asyncio.run(main())
