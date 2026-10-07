"""Проверки реальных HTTP-запросов стенда и транзакций PostgreSQL. Только вымышленные данные."""
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from jsonschema import Draft202012Validator

BASE=os.getenv('API_URL','http://localhost:8080')
PROVIDER=os.getenv('PROVIDER_URL','http://localhost:8081')
ADMIN={'X-Demo-Key':'local-demo-only'}
SERVICE={'X-Provider-Key':'provider-demo-only'}

@pytest.fixture(scope='session')
def spec():
    return httpx.get(BASE+'/openapi.json',timeout=10).json()

def call(method,path,*,expected=200,template=None,spec=None,**kwargs):
    r=httpx.request(method,BASE+path,timeout=15,**kwargs)
    assert r.status_code==expected,(method,path,r.status_code,r.text)
    if spec is not None and expected!=204:
        shape=spec['paths'][template or path][method.lower()]['responses'][str(expected)]['content']['application/json']['schema']
        Draft202012Validator({'components':spec['components'],**shape}).validate(r.json())
    return r

def account(email=None):
    email=email or f'{uuid4().hex}@example.test'
    ch=call('POST','/v1/auth/challenges',expected=202,json={'email':email}).json()['challengeId']
    code=call('GET',f'/demo/mailbox/{ch}',headers=ADMIN).json()['code']
    session=call('POST','/v1/auth/sessions',expected=201,json={'challengeId':ch,'code':code,'deviceLabel':'Тестовое устройство'}).json()
    return email,{'Authorization':'Bearer '+session['accessToken']},session

def buy(headers,key=None,plan='DEMO-30'):
    return call('POST','/v1/payments',expected=202,headers={**headers,'Idempotency-Key':key or str(uuid4())},json={'planCode':plan}).json()

def set_status(id_,status):
    r=httpx.post(PROVIDER+f'/demo/payments/{id_}',headers=ADMIN,json={'status':status},timeout=10)
    assert r.status_code==200,r.text

def notify(id_,event=None,**kwargs):
    return call('POST','/v1/provider/notifications',json={'eventId':event or str(uuid4()),'paymentId':id_},headers=SERVICE,**kwargs)

def test_registration_second_device_and_logout(spec):
    email,h,first=account()
    _,second,other=account(email)
    assert first['accountId']==other['accountId'] and first['accessToken']!=other['accessToken']
    call('GET','/v1/me',headers=h,spec=spec)
    call('DELETE','/v1/auth/sessions/current',headers=h,expected=204,spec=spec)
    call('GET','/v1/me',headers=h,expected=401,spec=spec)
    call('GET','/v1/me',headers=second,spec=spec)

def test_code_single_use_and_attempt_limit(spec):
    email=f'{uuid4().hex}@example.test'
    ch=call('POST','/v1/auth/challenges',expected=202,json={'email':email},spec=spec).json()['challengeId']
    code=call('GET',f'/demo/mailbox/{ch}',headers=ADMIN).json()['code']
    wrong='000000' if code!='000000' else '111111'
    for _ in range(5):
        call('POST','/v1/auth/sessions',expected=401,json={'challengeId':ch,'code':wrong,'deviceLabel':'d'},spec=spec)
    call('POST','/v1/auth/sessions',expected=401,json={'challengeId':ch,'code':code,'deviceLabel':'d'},spec=spec)
    ch=call('POST','/v1/auth/challenges',expected=202,json={'email':email}).json()['challengeId']
    code=call('GET',f'/demo/mailbox/{ch}',headers=ADMIN).json()['code']
    data={'challengeId':ch,'code':code,'deviceLabel':'d'}
    call('POST','/v1/auth/sessions',expected=201,json=data,spec=spec)
    call('POST','/v1/auth/sessions',expected=401,json=data,spec=spec)

def test_rate_limit(spec):
    email=f'{uuid4().hex}@example.test'
    for _ in range(5): call('POST','/v1/auth/challenges',expected=202,json={'email':email})
    call('POST','/v1/auth/challenges',expected=429,json={'email':email},spec=spec)

def test_pending_does_not_grant_access(spec):
    _,h,_=account(); p=buy(h)
    assert p['status']=='pending'
    call('GET','/v1/plans',spec=spec)
    call('GET',f'/v1/payments/{p["paymentId"]}',headers=h,template='/v1/payments/{payment_id}',spec=spec)
    assert call('GET','/v1/entitlements',headers=h,spec=spec).json()['paid'] is False

def test_idempotency_replay_and_conflict(spec):
    _,h,_=account(); key=str(uuid4()); p=buy(h,key)
    assert buy(h,key)['paymentId']==p['paymentId']
    call('POST','/v1/payments',expected=409,headers={**h,'Idempotency-Key':key},json={'planCode':'DEMO-60'},spec=spec)

def test_success_duplicate_different_event_second_device(spec):
    email,h,_=account(); p=buy(h); id_=p['paymentId']; event=str(uuid4())
    set_status(id_,'succeeded'); notify(id_,event,spec=spec)
    first=call('GET','/v1/entitlements',headers=h,spec=spec).json()
    assert first['paid']
    notify(id_,event); notify(id_)
    _,h2,_=account(email)
    assert call('GET','/v1/entitlements',headers=h2,spec=spec).json()['activeUntil']==first['activeUntil']

def test_concurrent_notifications_single_period():
    _,h,_=account(); p=buy(h); set_status(p['paymentId'],'succeeded')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:notify(p['paymentId']),range(4)))
    before=call('GET','/v1/entitlements',headers=h).json()['activeUntil']
    notify(p['paymentId'])
    assert call('GET','/v1/entitlements',headers=h).json()['activeUntil']==before

def test_concurrent_create_single_payment():
    _,h,_=account(); key=str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        values=list(pool.map(lambda _:buy(h,key)['paymentId'],range(4)))
    assert len(set(values))==1

def test_refund_does_not_resurrect_access(spec):
    _,h,_=account(); p=buy(h); id_=p['paymentId']
    set_status(id_,'succeeded'); notify(id_)
    set_status(id_,'refunded'); notify(id_); notify(id_)
    e=call('GET','/v1/entitlements',headers=h,spec=spec).json()
    assert not e['paid'] and 'journal.read' in e['features'] and 'journal.export' in e['features']

def test_canceled_does_not_grant():
    _,h,_=account(); p=buy(h); set_status(p['paymentId'],'canceled'); notify(p['paymentId'])
    assert not call('GET','/v1/entitlements',headers=h).json()['paid']

def test_isolation(spec):
    _,h,_=account(); _,other,_=account(); p=buy(h)
    call('GET',f'/v1/payments/{p["paymentId"]}',headers=other,expected=404,template='/v1/payments/{payment_id}',spec=spec)

@pytest.mark.parametrize('extra',[{'photo':'abc'},{'weightKg':96},{'amountMinor':1},{'accountId':str(uuid4())}])
def test_server_rejects_unexpected_fields(extra,spec):
    _,h,_=account()
    call('POST','/v1/payments',expected=422,headers={**h,'Idempotency-Key':str(uuid4())},json={'planCode':'DEMO-30',**extra},spec=spec)

def test_no_photo_or_journal_endpoint():
    for path in ('/v1/photos','/v1/workouts','/v1/measurements'):
        call('POST',path,expected=404,json={})

def test_notification_auth_and_unconfirmed_provider(spec):
    _,h,_=account(); p=buy(h)
    call('POST','/v1/provider/notifications',expected=403,headers={'X-Provider-Key':'wrong'},json={'eventId':str(uuid4()),'paymentId':p['paymentId']},spec=spec)
    notify(p['paymentId']) # Уведомление без подтверждённой оплаты не даёт доступа.
    assert not call('GET','/v1/entitlements',headers=h).json()['paid']

def test_missing_notification_reconciled():
    _,h,_=account(); p=buy(h); set_status(p['paymentId'],'succeeded')
    assert not call('GET','/v1/entitlements',headers=h).json()['paid']
    call('POST','/demo/reconcile',headers=ADMIN)
    assert call('GET','/v1/entitlements',headers=h).json()['paid']

def test_provider_timeout_keeps_same_payment(monkeypatch):
    from fastapi.testclient import TestClient
    import stand.api as api
    _,h,_=account(); key=str(uuid4()); old=api.provider_call
    def timeout(*args,**kwargs): api.reject(503,'PROVIDER_UNAVAILABLE')
    with TestClient(api.app) as client:
        monkeypatch.setattr(api,'provider_call',timeout)
        first=client.post('/v1/payments',headers={**h,'Idempotency-Key':key},json={'planCode':'DEMO-30'})
        assert first.status_code==202 and first.json()['status']=='creating'
        monkeypatch.setattr(api,'provider_call',old)
        second=client.post('/v1/payments',headers={**h,'Idempotency-Key':key},json={'planCode':'DEMO-30'})
        assert second.status_code==202 and second.json()['status']=='pending'
        assert first.json()['paymentId']==second.json()['paymentId']

def test_sql_integrity():
    import psycopg
    with psycopg.connect(os.environ['DATABASE_URL']) as c:
        for query in ["SELECT p.id FROM payments p LEFT JOIN subscription_periods s ON s.payment_id=p.id WHERE p.status='succeeded' AND s.payment_id IS NULL",
                      "SELECT p.id FROM payments p JOIN subscription_periods s ON s.payment_id=p.id WHERE p.status='refunded' AND NOT s.revoked"]:
            assert not c.execute(query).fetchall()
