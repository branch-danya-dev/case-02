"""Имитатор внешнего платёжного сервиса. Денег, карт и внешних запросов нет."""
import os
import hmac
import threading
from uuid import UUID
from fastapi import FastAPI, Header, Depends, HTTPException
from pydantic import Field
from typing import Literal
from stand.models import Strict
app=FastAPI(title='Имитатор платежей — не настоящая касса')
KEY=os.getenv('PROVIDER_KEY','provider-demo-only')
DEMO=os.getenv('DEMO_KEY','local-demo-only')
LOCK=threading.Lock()
PAYMENTS={}

def internal(x_provider_key:str=Header(alias='X-Provider-Key')):
    if not hmac.compare_digest(x_provider_key,KEY): raise HTTPException(403,'denied')

def demo(x_demo_key:str=Header(alias='X-Demo-Key')):
    if not hmac.compare_digest(x_demo_key,DEMO): raise HTTPException(403,'denied')

class Create(Strict):
    paymentId: UUID
    merchantRef: str
    amountMinor: int = Field(gt=0)
    currency: Literal['RUB']

class Change(Strict):
    status: Literal['succeeded','canceled','refunded']

@app.get('/health')
def health(): return {'status':'ok','mode':'demonstration'}

@app.post('/payments',dependencies=[Depends(internal)])
def create(body:Create):
    key=str(body.paymentId)
    with LOCK:
        fields=body.model_dump(mode='json')
        if key in PAYMENTS:
            if any(PAYMENTS[key][f]!=v for f,v in fields.items()): raise HTTPException(409,'conflict')
        else: PAYMENTS[key]={**fields,'status':'pending'}
        return PAYMENTS[key]

@app.get('/payments/{id_}',dependencies=[Depends(internal)])
def get(id_:UUID):
    with LOCK:
        if str(id_) not in PAYMENTS: raise HTTPException(404,'not found')
        return PAYMENTS[str(id_)]

@app.post('/demo/payments/{id_}',dependencies=[Depends(demo)])
def change(id_:UUID,body:Change):
    with LOCK:
        row=PAYMENTS.get(str(id_))
        if row is None: raise HTTPException(404,'not found')
        allowed={'pending':{'succeeded','canceled'},'succeeded':{'refunded'},'canceled':set(),'refunded':set()}
        if body.status!=row['status'] and body.status not in allowed[row['status']]: raise HTTPException(409,'invalid transition')
        row['status']=body.status
        return row

@app.get('/demo/checkout/{id_}')
def checkout(id_:UUID):
    return {'notice':'Это имитация. Не вводите данные карты. Измените исход через /demo/payments/{id}.','paymentId':str(id_)}
