"""Дополнительная проверка границы срока кода. Только PostgreSQL демонстрационного стенда."""
import os
from uuid import uuid4
import httpx
import psycopg
BASE=os.getenv('API_URL','http://localhost:8080')

def test_expired_code_rejected():
    r=httpx.post(BASE+'/v1/auth/challenges',json={'email':f'{uuid4().hex}@example.test'},timeout=10)
    assert r.status_code==202
    id_=r.json()['challengeId']
    r=httpx.get(BASE+'/demo/mailbox/'+id_,headers={'X-Demo-Key':'local-demo-only'},timeout=10)
    assert r.status_code==200
    code=r.json()['code']
    with psycopg.connect(os.environ['DATABASE_URL']) as c:
        c.execute("UPDATE challenges SET expires_at=now()-interval '1 second' WHERE id=%s",(id_,))
    r=httpx.post(BASE+'/v1/auth/sessions',json={'challengeId':id_,'code':code,'deviceLabel':'Тест'},timeout=10)
    assert r.status_code==401 and r.json()['code']=='CODE_INVALID'
