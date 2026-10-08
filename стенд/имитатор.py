"""Имитатор внешнего платёжного сервиса. Денег, карт и внешних запросов нет."""
import os
import hmac
import threading
from uuid import UUID
from fastapi import FastAPI, Header, Depends, HTTPException
from pydantic import Field
from typing import Literal
from стенд.модели import Strict
app=FastAPI(title='Имитатор платежей — не настоящая касса')
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from стенд.локализация import localize_openapi
_original_openapi=app.openapi
app.openapi=lambda:localize_openapi(_original_openapi())

@app.exception_handler(RequestValidationError)
async def invalid_input(_, exc):
    return JSONResponse(status_code=422,content={'detail':'Проверьте состав и значения полей запроса; лишние поля запрещены'})

KEY=os.getenv('PROVIDER_KEY','provider-demo-only')
DEMO=os.getenv('DEMO_KEY','local-demo-only')
LOCK=threading.Lock()
PAYMENTS={}

def internal(x_provider_key:str=Header(alias='X-Provider-Key')):
    if not hmac.compare_digest(x_provider_key,KEY): raise HTTPException(403,'Доступ запрещён')

def demo(x_demo_key:str=Header(alias='X-Demo-Key')):
    if not hmac.compare_digest(x_demo_key,DEMO): raise HTTPException(403,'Доступ запрещён')

class Create(Strict):
    paymentId: UUID
    merchantRef: str
    amountMinor: int = Field(gt=0)
    currency: Literal['RUB']

class Change(Strict):
    status: Literal['succeeded','canceled','refunded']

@app.get('/health',summary='Проверить доступность имитатора')
def health(): return {'status':'ok','mode':'demonstration'}

@app.post('/payments',dependencies=[Depends(internal)],summary='Создать демонстрационный платёж')
def create(body:Create):
    key=str(body.paymentId)
    with LOCK:
        fields=body.model_dump(mode='json')
        if key in PAYMENTS:
            if any(PAYMENTS[key][f]!=v for f,v in fields.items()): raise HTTPException(409,'Повторный запрос содержит другие данные')
        else: PAYMENTS[key]={**fields,'status':'pending'}
        return PAYMENTS[key]

@app.get('/payments/{id_}',dependencies=[Depends(internal)],summary='Получить сведения о демонстрационном платеже')
def get(id_:UUID):
    with LOCK:
        if str(id_) not in PAYMENTS: raise HTTPException(404,'Платёж не найден')
        return PAYMENTS[str(id_)]

@app.post('/demo/payments/{id_}',dependencies=[Depends(demo)],summary='Изменить исход демонстрационной оплаты')
def change(id_:UUID,body:Change):
    with LOCK:
        row=PAYMENTS.get(str(id_))
        if row is None: raise HTTPException(404,'Платёж не найден')
        allowed={'pending':{'succeeded','canceled'},'succeeded':{'refunded'},'canceled':set(),'refunded':set()}
        if body.status!=row['status'] and body.status not in allowed[row['status']]: raise HTTPException(409,'Недопустимое изменение состояния платежа')
        row['status']=body.status
        return row

@app.get('/demo/checkout/{id_}',summary='Открыть пояснение к имитации оплаты')
def checkout(id_:UUID):
    return {'notice':'Это имитация. Не вводите данные карты. Измените исход через /demo/payments/{id}.','paymentId':str(id_)}
