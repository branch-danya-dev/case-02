"""Исполняемая модель контрактов, НЕ сервер приложения trening. Только изолированный стенд."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
import httpx
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Depends, Header, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from stand.models import (Error, ChallengeIn, ChallengeOut, LoginIn, SessionOut,
                          AccountOut, Plan, PaymentIn, PaymentOut, Notification,
                          Ack, Entitlement, paid_until, next_period)

app = FastAPI(title='Кейс 02: регистрация, оплата и доступ', version='1.0.0',
              description='Исполняемая демонстрация проектируемого контракта. Не принимает настоящие платежи. Тренировочные данные API не принимает.',
              responses={s:{'model':Error} for s in (400,401,403,404,409,422,429,503)})
app.openapi_version = '3.1.1'
security = HTTPBearer(auto_error=False)
DSN = os.getenv('DATABASE_URL','postgresql://case:case-demo-only@localhost:5432/case02')
PROVIDER = os.getenv('PROVIDER_URL','http://localhost:8081')
DEMO_KEY = os.getenv('DEMO_KEY','local-demo-only')
PROVIDER_KEY = os.getenv('PROVIDER_KEY','provider-demo-only')
MAILBOX = {} # Имитация почты; только адреса example.test, только /demo/.

def now():
    return datetime.now(timezone.utc)

def db():
    return psycopg.connect(DSN, row_factory=dict_row)

def reject(status, code):
    raise HTTPException(status, code)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def code_hash(id_, code):
    return hmac.new(DEMO_KEY.encode(), f'{id_}:{code}'.encode(), hashlib.sha256).hexdigest()

@app.exception_handler(HTTPException)
async def http_error(_, exc):
    return JSONResponse(status_code=exc.status_code, content={'code':str(exc.detail),'message':str(exc.detail)}, headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def validation_error(_, exc):
    # Не отражаем содержимое тела, email, код и ключ сеанса в ответе/журнале.
    return JSONResponse(status_code=422, content={'code':'INVALID_INPUT','message':'Проверьте поля по контракту; лишние поля запрещены'})

def demo(x_demo_key: str | None = Header(default=None)):
    if not x_demo_key or not hmac.compare_digest(x_demo_key, DEMO_KEY):
        reject(403,'DEMO_ACCESS_DENIED')

def auth(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials is None or credentials.scheme.lower() != 'bearer':
        reject(401,'AUTH_REQUIRED')
    with db() as c:
        row = c.execute('SELECT * FROM sessions WHERE token_hash=%s AND expires_at>%s',
                        (digest(credentials.credentials),now())).fetchone()
    if not row:
        reject(401,'SESSION_INVALID')
    return row

@app.get('/health', include_in_schema=False)
def health():
    with db() as c:
        c.execute('SELECT 1')
    return {'status':'ok','mode':'demonstration'}

@app.post('/v1/auth/challenges', response_model=ChallengeOut, status_code=202,
          summary='Запросить код входа или регистрации', operation_id='requestChallenge', tags=['Вход'])
def challenge(body: ChallengeIn):
    email=body.email.strip().lower()
    if not email.endswith('@example.test'):
        reject(422,'DEMO_EMAIL_ONLY')
    id_=uuid4(); code=f'{secrets.randbelow(1000000):06d}'
    with db() as c:
        # Сериализация запросов по email закрывает гонку ограничения частоты.
        c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(email,))
        n=c.execute('SELECT count(*) AS n FROM challenges WHERE email=%s AND created_at>%s',
                    (email,now()-timedelta(minutes=10))).fetchone()['n']
        if n>=5:
            reject(429,'TRY_LATER')
        c.execute('INSERT INTO challenges(id,email,code_hash,expires_at) VALUES(%s,%s,%s,%s)',
                  (id_,email,code_hash(id_,code),now()+timedelta(minutes=10)))
    MAILBOX[str(id_)]=code
    return {'challengeId':id_,'expiresInSeconds':600}

@app.get('/demo/mailbox/{challenge_id}', dependencies=[Depends(demo)], include_in_schema=False)
def mailbox(challenge_id: UUID):
    code=MAILBOX.get(str(challenge_id))
    if code is None: reject(404,'CODE_NOT_FOUND')
    return {'code':code}

@app.post('/v1/auth/sessions',response_model=SessionOut,status_code=201,
          summary='Подтвердить код и открыть сеанс на устройстве',operation_id='openSession',tags=['Вход'])
def login(body: LoginIn):
    failure=False
    with db() as c:
        item=c.execute('SELECT * FROM challenges WHERE id=%s FOR UPDATE',(body.challengeId,)).fetchone()
        if not item or item['used'] or item['expires_at']<=now() or item['attempts']>=5:
            reject(401,'CODE_INVALID')
        if not hmac.compare_digest(item['code_hash'],code_hash(body.challengeId,body.code)):
            c.execute('UPDATE challenges SET attempts=attempts+1 WHERE id=%s',(body.challengeId,))
            failure=True
        else:
            c.execute('UPDATE challenges SET used=true WHERE id=%s',(body.challengeId,))
            account=c.execute('INSERT INTO accounts(id,email) VALUES(%s,%s) ON CONFLICT(email) DO UPDATE SET email=EXCLUDED.email RETURNING id',
                              (uuid4(),item['email'])).fetchone()['id']
            token=secrets.token_urlsafe(32); expires=now()+timedelta(hours=8)
            c.execute('INSERT INTO sessions VALUES(%s,%s,%s,%s,%s)',(uuid4(),account,digest(token),body.deviceLabel,expires))
    # Неверная попытка уже зафиксирована; исключение внутри транзакции откатило бы счётчик.
    if failure: reject(401,'CODE_INVALID')
    MAILBOX.pop(str(body.challengeId),None)
    return {'accountId':account,'accessToken':token,'expiresAt':expires}

@app.delete('/v1/auth/sessions/current',status_code=204,
            summary='Завершить текущий сеанс',operation_id='closeSession',tags=['Вход'])
def logout(session=Depends(auth)):
    with db() as c: c.execute('DELETE FROM sessions WHERE id=%s',(session['id'],))
    return Response(status_code=204)

@app.get('/v1/me',response_model=AccountOut,summary='Получить свою учётную запись',operation_id='getAccount',tags=['Вход'])
def me(session=Depends(auth)):
    with db() as c: row=c.execute('SELECT email FROM accounts WHERE id=%s',(session['account_id'],)).fetchone()
    return {'accountId':session['account_id'],'email':row['email']}

@app.get('/v1/plans',response_model=list[Plan],summary='Получить условные тарифы',operation_id='listPlans',tags=['Оплата'])
def plans():
    with db() as c: rows=c.execute('SELECT * FROM plans ORDER BY code').fetchall()
    return [{'code':r['code'],'amountMinor':r['amount_minor'],'currency':r['currency'],
             'durationSeconds':r['duration_seconds']} for r in rows]

def pay_view(row):
    return {'paymentId':row['id'],'status':row['status'],'amountMinor':row['amount_minor'],
            'currency':row['currency'],'checkoutUrl':f'http://localhost:8081/demo/checkout/{row["id"]}' if row['status']=='pending' else None}

def provider_call(method,path,body=None):
    try:
        r=httpx.request(method,PROVIDER+path,json=body,headers={'X-Provider-Key':PROVIDER_KEY},timeout=3)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError,ValueError):
        reject(503,'PROVIDER_UNAVAILABLE')

def ensure_created(id_):
    with db() as c: row=c.execute('SELECT * FROM payments WHERE id=%s',(id_,)).fetchone()
    if row['status']!='creating': return
    provider_call('POST','/payments',{'paymentId':str(id_),'merchantRef':str(id_),
                  'amountMinor':row['amount_minor'],'currency':row['currency']})
    with db() as c: c.execute("UPDATE payments SET status='pending' WHERE id=%s AND status='creating'",(id_,))

@app.post('/v1/payments',response_model=PaymentOut,status_code=202,
          summary='Создать или повторить запрос оплаты',operation_id='createPayment',tags=['Оплата'])
def pay(body:PaymentIn,idempotency_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=64),session=Depends(auth)):
    account=session['account_id']
    with db() as c:
        c.execute('SELECT id FROM accounts WHERE id=%s FOR UPDATE',(account,))
        row=c.execute('SELECT * FROM payments WHERE account_id=%s AND idempotency_key=%s',(account,idempotency_key)).fetchone()
        if row and row['plan_code']!=body.planCode: reject(409,'IDEMPOTENCY_CONFLICT')
        if not row:
            plan=c.execute('SELECT * FROM plans WHERE code=%s',(body.planCode,)).fetchone()
            if not plan: reject(404,'PLAN_NOT_FOUND')
            row=c.execute("INSERT INTO payments VALUES(%s,%s,%s,%s,%s,%s,%s,'creating',now()) RETURNING *",
                           (uuid4(),account,plan['code'],idempotency_key,plan['amount_minor'],plan['currency'],plan['duration_seconds'])).fetchone()
    try: ensure_created(row['id'])
    except HTTPException as e:
        if e.status_code!=503: raise
        # Исход неизвестен. Запись сохранена, новый платёж автоматически не создаётся.
    with db() as c: row=c.execute('SELECT * FROM payments WHERE id=%s',(row['id'],)).fetchone()
    return pay_view(row)

@app.get('/v1/payments/{payment_id}',response_model=PaymentOut,
         summary='Получить состояние своего платежа',operation_id='getPayment',tags=['Оплата'])
def payment(payment_id:UUID,session=Depends(auth)):
    with db() as c: row=c.execute('SELECT * FROM payments WHERE id=%s AND account_id=%s',(payment_id,session['account_id'])).fetchone()
    if not row: reject(404,'PAYMENT_NOT_FOUND')
    return pay_view(row)

def apply_notice(body):
    # Уведомление лишь повод свериться. Статус, сумма и ссылка получаются у имитатора по защищённому внутреннему запросу.
    proof=provider_call('GET',f'/payments/{body.paymentId}')
    with db() as c:
        row=c.execute('SELECT * FROM payments WHERE id=%s',(body.paymentId,)).fetchone()
        if not row: reject(404,'PAYMENT_NOT_FOUND')
        c.execute('SELECT id FROM accounts WHERE id=%s FOR UPDATE',(row['account_id'],))
        row=c.execute('SELECT * FROM payments WHERE id=%s FOR UPDATE',(body.paymentId,)).fetchone()
        if (proof.get('merchantRef')!=str(row['id']) or proof.get('amountMinor')!=row['amount_minor'] or proof.get('currency')!=row['currency']):
            reject(409,'PROVIDER_PROOF_MISMATCH')
        previous=c.execute('SELECT payment_id FROM provider_events WHERE id=%s',(body.eventId,)).fetchone()
        if previous and previous['payment_id']!=body.paymentId: reject(409,'EVENT_CONFLICT')
        if previous: return
        c.execute('INSERT INTO provider_events(id,payment_id) VALUES(%s,%s)',(body.eventId,body.paymentId))
        state=proof.get('status')
        if state not in ('pending','succeeded','canceled','refunded'): reject(409,'PROVIDER_STATUS_INVALID')
        if row['status']=='refunded': return
        if state=='refunded':
            c.execute("UPDATE payments SET status='refunded' WHERE id=%s",(row['id'],))
            c.execute('UPDATE subscription_periods SET revoked=true WHERE payment_id=%s',(row['id'],))
        elif state=='succeeded':
            exists=c.execute('SELECT 1 FROM subscription_periods WHERE payment_id=%s',(row['id'],)).fetchone()
            if not exists:
                periods=c.execute('SELECT starts_at,ends_at FROM subscription_periods WHERE account_id=%s AND NOT revoked',(row['account_id'],)).fetchall()
                start,end=next_period([(p['starts_at'],p['ends_at']) for p in periods],now(),row['duration_seconds'])
                c.execute('INSERT INTO subscription_periods VALUES(%s,%s,%s,%s,false)',(row['id'],row['account_id'],start,end))
            c.execute("UPDATE payments SET status='succeeded' WHERE id=%s",(row['id'],))
        elif row['status'] not in ('succeeded','canceled'):
            c.execute('UPDATE payments SET status=%s WHERE id=%s',(state,row['id']))

@app.post('/v1/provider/notifications',response_model=Ack,
          summary='Получить сигнал платёжной системы и проверить его',operation_id='acceptNotification',tags=['Интеграция'])
def notice(body:Notification,x_provider_key:str=Header(alias='X-Provider-Key')):
    if not hmac.compare_digest(x_provider_key,PROVIDER_KEY): reject(403,'PROVIDER_ACCESS_DENIED')
    apply_notice(body)
    return Ack()

@app.get('/v1/entitlements',response_model=Entitlement,
         summary='Получить свои права доступа на текущий момент',operation_id='getEntitlements',tags=['Подписка'])
def entitlements(session=Depends(auth)):
    with db() as c:
        periods=c.execute('SELECT starts_at,ends_at FROM subscription_periods WHERE account_id=%s AND NOT revoked',(session['account_id'],)).fetchall()
    end=paid_until([(p['starts_at'],p['ends_at']) for p in periods],now())
    return {'accountId':session['account_id'],'paid':end is not None,'activeUntil':end,
            'features':['journal.read','journal.export']+(['forecast.advanced','body3d.compare'] if end else [])}

@app.post('/demo/reconcile',dependencies=[Depends(demo)],include_in_schema=False)
def reconcile():
    with db() as c: rows=c.execute("SELECT id FROM payments WHERE status IN ('creating','pending','succeeded')").fetchall()
    checked=0
    for row in rows:
        try:
            ensure_created(row['id'])
            apply_notice(Notification(eventId=uuid4(),paymentId=row['id']))
            checked+=1
        except HTTPException:
            continue
    return {'checked':checked}
