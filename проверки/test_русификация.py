"""Перевод не должен менять протокол, доступ или результаты операций."""
import hashlib
import json
import re
from pathlib import Path
from fastapi.testclient import TestClient
from стенд.сервер import app
from стенд.локализация import ERROR_MESSAGES, FIELDS
from стенд.модели import Workout, Estimate

ROOT=Path(__file__).resolve().parents[1]

def protocol(value):
    if isinstance(value,dict):
        return {k:protocol(v) for k,v in value.items() if k not in {'title','description','summary','examples','example'}}
    if isinstance(value,list): return [protocol(v) for v in value]
    return value

def test_protocol_unchanged():
    expected=json.loads((ROOT/'проверки/контроль-протокола.json').read_text(encoding='utf-8'))['sha256']
    actual=hashlib.sha256(json.dumps(protocol(app.openapi()),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assert actual==expected,'Русификация изменила машинный протокол'

def test_error_message_is_russian_and_code_stable():
    with TestClient(app) as client:
        r=client.get('/v1/me')
    assert r.status_code==401
    assert r.json()=={'code':'AUTH_REQUIRED','message':ERROR_MESSAGES['AUTH_REQUIRED']}
    assert re.search('[А-Яа-яЁё]',r.json()['message'])

def test_validation_message_is_russian():
    with TestClient(app) as client:
        r=client.post('/v1/auth/challenges',json={})
    assert r.status_code==422 and r.json()['code']=='INVALID_INPUT'
    assert re.search('[А-Яа-яЁё]',r.json()['message'])

def test_all_known_errors_have_translations():
    source=(ROOT/'стенд/сервер.py').read_text(encoding='utf-8')
    codes=set(re.findall(r"reject\(\s*\d+\s*,\s*'([A-Z_]+)'",source))
    assert codes<=ERROR_MESSAGES.keys()
    assert all(re.search('[А-Яа-яЁё]',v) for v in ERROR_MESSAGES.values())

def test_schema_captions_are_russian():
    for schema in [*app.openapi()['components']['schemas'].values(),Workout.model_json_schema(),Estimate.model_json_schema()]:
        for name,field in schema.get('properties',{}).items():
            assert name in FIELDS,f'Поле без перевода: {name}'
            assert field.get('title')==FIELDS[name]
            assert re.search('[А-Яа-яЁё]',field.get('description',''))

def test_russian_structure_and_reference():
    assert all(not (ROOT/p).exists() for p in ['docs','contracts','diagrams','planning','portfolio','schema','stand','tests','tools'])
    assert all((ROOT/p).is_file() for p in ['интерфейсы/README.md','планирование/доска.html','представление/Рогулин-Даниил-кейс-02.pdf','сборка/собрать.py','проверки/проверить.py'])


def test_parameter_captions_are_russian():
    for item in app.openapi()['paths'].values():
        for operation in item.values():
            if not isinstance(operation,dict): continue
            for parameter in operation.get('parameters',[]):
                name=parameter['name']
                assert name in FIELDS
                assert parameter['schema']['title']==FIELDS[name]
                assert re.search('[А-Яа-яЁё]',parameter['description'])
