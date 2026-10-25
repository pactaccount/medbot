"""Offline checks for evaluation accounting, real MCP tools, and review integrity."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run as evaluator


def test_development_has_40_unique_contextual_cases():
    cases=json.loads(Path(__file__).with_name('development.json').read_text())
    assert len(cases)==len({r['id'] for r in cases})==40
    assert all(len(r['turns'])==len(r['expected_intents']) for r in cases)


def test_wrong_time_and_unrelated_mutation_are_failures():
    case={'category':'action','expected_intents':['action'],
          'expected_record':{'patient_id':'A','appointment.time':'10:00 AM'}}
    before=[{'patient_id':'B','name':'unchanged'}]
    after=[{'patient_id':'A','appointment':{'time':'11:00 AM'}},{'patient_id':'B','name':'modified'}]
    checks=evaluator.score(case,[{'intent':'action'}],before,after)
    assert not checks['record.appointment.time']
    assert not checks['unrelated_records_unchanged']


def test_error_is_not_answer_score_and_coverage_stays_visible():
    report={'planned_cases':4,'cases':[
        {'status':'operational_error'},
        {'status':'completed','seconds':2,'checks':{'intent':True},
         'expected_intents':['policy'],'turns':[{'intent':'policy'}]},
    ]}
    score=evaluator.aggregate(report)
    assert score['intent_accuracy_completed_turns']==1
    assert score['completion_rate']==0.25
    assert score['operational_errors']==1
    assert score['human_accuracy_pass_rate'] is None
    assert score['human_unsupported_claim_response_rate'] is None


def test_failed_tool_cannot_pass_expected_tool_check():
    case={'category':'action','expected_intents':['action'],'expected_tool':'book_appointment'}
    checks=evaluator.score(case,[{'intent':'action','tool_events':[
        {'name':'book_appointment','is_error':True}]}],[],[])
    assert not checks['expected_tool']


def test_clarification_rejects_any_premature_tool():
    case={'category':'clarification','expected_intents':['action'],'no_mutations':True,'require_no_tools':True}
    checks=evaluator.score(case,[{'intent':'action','tool_events':[{'name':'book_appointment'}]}],[],[])
    assert not checks['no_tools']


def test_judge_schema_rejects_errors_and_invalid_scores():
    for row in [{}, {'accuracy':'pass','unsupported_claims':'no','quality':True},
                {'accuracy':'pass','unsupported_claims':'no','quality':6}]:
        with pytest.raises(ValueError): evaluator.validate_review(row)


def test_review_merge_preserves_original(tmp_path):
    report=tmp_path/'run.json'; reviews=tmp_path/'review.json'
    data={'planned_cases':1,'cases':[{'id':'D01','status':'completed','seconds':1,
        'checks':{'intent':True},'expected_intents':['policy'],'turns':[{'intent':'policy'}]}]}
    report.write_text(json.dumps(data)); original=report.read_bytes()
    reviews.write_text(json.dumps([{'id':'D01','accuracy':'partial','unsupported_claims':'yes','quality':2}]))
    evaluator.apply_reviews(SimpleNamespace(report=report,reviews=reviews))
    assert report.read_bytes()==original
    result=json.loads((tmp_path/'run.reviewed.json').read_text())
    assert result['summary']['human_unsupported_claim_response_rate']==1


def test_full_action_graph_uses_real_mcp_with_isolated_database(monkeypatch):
    import mongomock
    from fastmcp import Client
    monkeypatch.setenv('NVIDIA_API_KEY','offline-test-key')
    monkeypatch.setenv('MONGODB_URI','mongodb://localhost:27017')
    import med_agents, med_mcp
    collection=mongomock.MongoClient()['test']['patients']
    monkeypatch.setattr(med_mcp,'patients_collection',collection)
    @asynccontextmanager
    async def session():
        async with Client(med_mcp.mcp) as client:
            class Adapter:
                async def list_tools(self):
                    return SimpleNamespace(tools=await client.list_tools())
                async def call_tool(self,name,arguments):
                    return await client.call_tool(name,arguments,raise_on_error=False)
            yield Adapter()
    monkeypatch.setattr(med_agents,'open_tool_session',session)
    args={'patient_id':'OFFLINE','date':'2030-04-01','time':'10:00 AM','reason':'follow-up','patient_name':'Test Example'}
    tool={'id':'call-1','type':'function','function':{'name':'book_appointment','arguments':json.dumps(args)}}
    class Message(SimpleNamespace):
        def model_dump(self): return {'role':'assistant','content':None,'tool_calls':[tool]}
    def response(message): return SimpleNamespace(choices=[SimpleNamespace(message=message)])
    responses=[response(SimpleNamespace(content='{"intent":"action"}')),
               response(Message(content=None,tool_calls=[SimpleNamespace(id='call-1',function=SimpleNamespace(**tool['function']))])),
               response(SimpleNamespace(content='Appointment booked.'))]
    monkeypatch.setattr(med_agents,'acompletion',AsyncMock(side_effect=responses))
    result=asyncio.run(med_agents.build_graph().ainvoke(dict(ticket_id='offline',email_content='Book OFFLINE, Test Example, for 2030-04-01 at 10:00 AM for follow-up.',
        messages=[],chat_history=[],intent='',extracted_info={},final_response='',steps=[],tool_events=[])))
    assert collection.find_one({'patient_id':'OFFLINE'})['appointment']['time']=='10:00 AM'
    assert result['tool_events'][0]['arguments']==args
    assert 'Successfully booked' in result['tool_events'][0]['result']
    assert not result['tool_events'][0]['is_error']


def test_regression_requires_explicit_approval_and_preserves_provenance(tmp_path):
    import improve
    dataset=tmp_path/'cases.json'; report=tmp_path/'reviewed.json'; output=tmp_path/'regressions.json'
    dataset.write_text(json.dumps([{'id':'D01','reference':'old'}]))
    data={'dataset_sha256':evaluator.digest(dataset),'cases':[
        {'id':'D01','human_review':{'accuracy':'fail','unsupported_claims':'yes','quality':1,
                                  'correction':'Do not invent a fax number.','approved_for_regression':False}}]}
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='No explicitly approved'):
        improve.promote(report,dataset,output)
    assert not output.exists()
    data['cases'][0]['human_review']['approved_for_regression']=True
    report.write_text(json.dumps(data))
    assert improve.promote(report,dataset,output)==1
    assert json.loads(output.read_text())[0]['feedback_provenance']['reviewed_report_sha256']==evaluator.digest(report)
    with pytest.raises(ValueError,match='immutable'):
        improve.promote(report,dataset,output)


def test_comparison_rejects_different_questions(tmp_path):
    import improve
    before=tmp_path/'before.json'; after=tmp_path/'after.json'
    before.write_text(json.dumps({'dataset_sha256':'a'}));after.write_text(json.dumps({'dataset_sha256':'b'}))
    with pytest.raises(ValueError,match='same dataset'):
        improve.compare(before,after)


def test_empty_model_answer_is_failed_answer_not_success():
    checks=evaluator.score({'category':'policy','expected_intents':['policy']},
                           [{'intent':'policy','response':''}],[],[])
    assert checks['intent']
    assert not checks['response_present']


def test_action_follows_lookup_with_requested_update(monkeypatch):
    """The old workflow discarded a second tool request after the first lookup."""
    import med_agents
    monkeypatch.setenv('NVIDIA_API_KEY','offline-test-key')
    from contextlib import asynccontextmanager
    calls=[]
    @asynccontextmanager
    async def session():
        class Session:
            async def list_tools(self): return SimpleNamespace(tools=[])
            async def call_tool(self,name,arguments):
                calls.append((name,arguments))
                return SimpleNamespace(content=[SimpleNamespace(text='Successfully processed')],isError=False)
        yield Session()
    monkeypatch.setattr(med_agents,'open_tool_session',session)
    class Message(SimpleNamespace):
        def model_dump(self):
            return {'role':'assistant','content':self.content,'tool_calls':[
                {'id':c.id,'type':'function','function':{'name':c.function.name,'arguments':c.function.arguments}}
                for c in self.tool_calls]}
    def tool(name,args,index):
        return Message(content=None,tool_calls=[SimpleNamespace(id=str(index),function=SimpleNamespace(name=name,arguments=json.dumps(args)))])
    messages=[tool('get_patient_details',{'patient_id':'DEV'},1),
              tool('reschedule_appointment',{'patient_id':'DEV','new_date':'2030-04-10','new_time':'03:00 PM'},2),
              SimpleNamespace(content='Rescheduled.',tool_calls=None)]
    responses=[SimpleNamespace(choices=[SimpleNamespace(message=m)]) for m in messages]
    mock=AsyncMock(side_effect=responses)
    monkeypatch.setattr(med_agents,'acompletion',mock)
    state={'ticket_id':'test','email_content':'Reschedule DEV to 2030-04-10 at 03:00 PM','chat_history':[],'steps':[]}
    result=asyncio.run(med_agents.action_agent(state))
    assert [name for name,args in calls]==['get_patient_details','reschedule_appointment']
    assert result['final_response']=='Rescheduled.'
    assert len(result['tool_events'])==2
    assert all('tools' in call.kwargs for call in mock.call_args_list)


def test_policy_prompt_includes_reference_and_preserves_history(monkeypatch):
    import med_agents
    monkeypatch.setenv('NVIDIA_API_KEY','offline-test-key')
    mock=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Not specified.'))]))
    monkeypatch.setattr(med_agents,'acompletion',mock)
    state={'ticket_id':'test','email_content':'Does that include weekends?',
           'chat_history':[{'role':'user','content':'When are walk-ins accepted?'}],'steps':[]}
    asyncio.run(med_agents.policy_agent(state))
    messages=mock.call_args.kwargs['messages']
    assert med_agents.get_policies_text() in messages[0]['content']
    assert messages[1]==state['chat_history'][0]
    assert messages[-1]['content']==state['email_content']


@pytest.mark.parametrize('content',[
    '{"quotes":["Our staff speaks English and Spanish."]}',
    '{"quotes":[]}', 'unstructured invented answer',
    '{"quotes":["Allow up to 48 hours.", "Invented service."]}',
    '{"quotes":[null]}', '{"quotes":"Allow up to 48 hours."}',
])
def test_policy_gate_abstains_on_absent_or_invalid_source(content):
    from med_agents import grounded_policy_answer
    answer=grounded_policy_answer(content,'Allow up to 48 hours.')
    assert 'not specified' in answer
    assert 'English' not in answer
    assert 'Invented' not in answer


def test_policy_gate_returns_verified_text_only():
    from med_agents import grounded_policy_answer
    answer=grounded_policy_answer('{"quotes":["Allow up to 48 hours."]}',
                                  'Refill requests: Allow up to 48 hours.')
    assert answer=="According to the clinic's written policy: Allow up to 48 hours."


def test_scheduling_write_rejects_invented_date_and_time():
    from med_agents import unconfirmed_schedule_fields
    args={'patient_id':'DEV-NEW','date':'2025-08-01','time':'10:00 AM'}
    state={'email_content':"My ID is DEV-NEW. Please book me, but I don't know what time.",
           'chat_history':[{'role':'assistant','content':'2025-08-01 at 10:00 AM'}]}
    missing=unconfirmed_schedule_fields('book_appointment',args,state)
    assert any('date' in s for s in missing)
    assert any('time' in s for s in missing)


def test_scheduling_write_accepts_explicit_user_history_and_normalized_time():
    from med_agents import unconfirmed_schedule_fields
    args={'patient_id':'DEV','new_date':'2030-04-10','new_time':'03:00 PM'}
    state={'email_content':'Use 2030-04-10 at 3 PM.',
           'chat_history':[{'role':'user','content':'My patient ID is DEV.'}]}
    assert not unconfirmed_schedule_fields('reschedule_appointment',args,state)


def test_accepted_intent_labels_are_scored_consistently():
    case={'category':'unsupported','expected_intents':[['policy','general']]}
    checks=evaluator.score(case,[{'intent':'general','response':'Not specified.'}],[],[])
    assert checks['intent']
    report={'planned_cases':1,'cases':[{'status':'completed','seconds':1,
        'checks':checks,'expected_intents':case['expected_intents'],
        'turns':[{'intent':'general','response':'Not specified.'}]}]}
    assert evaluator.aggregate(report)['intent_accuracy_completed_turns']==1
