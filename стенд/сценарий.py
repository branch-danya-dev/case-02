"""Один показательный сценарий без настоящей почты и денег. Запуск: python -m стенд.сценарий"""
import os
from uuid import uuid4
import httpx
from стенд.локализация import STATUS_LABELS
BASE=os.getenv('API_URL','http://localhost:8080')
PROVIDER=os.getenv('PROVIDER_URL','http://localhost:8081')
ADMIN={'X-Demo-Key':'local-demo-only'}

def req(method,url,**kwargs):
    r=httpx.request(method,url,timeout=10,**kwargs); r.raise_for_status(); return r.json()

def login(email,device):
    c=req('POST',BASE+'/v1/auth/challenges',json={'email':email})
    code=req('GET',BASE+'/demo/mailbox/'+c['challengeId'],headers=ADMIN)['code']
    s=req('POST',BASE+'/v1/auth/sessions',json={'challengeId':c['challengeId'],'code':code,'deviceLabel':device})
    return {'Authorization':'Bearer '+s['accessToken']}

def main():
    email=f'{uuid4().hex}@example.test'; h=login(email,'Телефон'); key=str(uuid4())
    p=req('POST',BASE+'/v1/payments',headers={**h,'Idempotency-Key':key},json={'planCode':'DEMO-30'})
    print('1. Создан платёж:',STATUS_LABELS.get(p['status'],p['status']))
    assert not req('GET',BASE+'/v1/entitlements',headers=h)['paid']
    req('POST',PROVIDER+'/demo/payments/'+p['paymentId'],headers=ADMIN,json={'status':'succeeded'})
    notice={'eventId':str(uuid4()),'paymentId':p['paymentId']}
    for _ in range(2): req('POST',BASE+'/v1/provider/notifications',headers={'X-Provider-Key':'provider-demo-only'},json=notice)
    second=login(email,'Компьютер')
    a=req('GET',BASE+'/v1/entitlements',headers=h); b=req('GET',BASE+'/v1/entitlements',headers=second)
    assert a['paid'] and a['activeUntil']==b['activeUntil']
    print('2. Два уведомления обработаны; доступ одинаков на двух устройствах.')
    req('POST',PROVIDER+'/demo/payments/'+p['paymentId'],headers=ADMIN,json={'status':'refunded'})
    req('POST',BASE+'/v1/provider/notifications',headers={'X-Provider-Key':'provider-demo-only'},json={'eventId':str(uuid4()),'paymentId':p['paymentId']})
    end=req('GET',BASE+'/v1/entitlements',headers=second)
    assert not end['paid'] and 'journal.export' in end['features']
    print('3. Возврат отозвал платный доступ; чтение и выгрузка дневника сохранены.')
    print('Тренировки, фотографии и данные карты не передавались. Это проверка стенда.')
if __name__=='__main__': main()
