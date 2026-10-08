"""Однократный перевод структуры и текстов. Протокол и правила оплаты не меняются."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIRS = {'contracts':'интерфейсы','diagrams':'схемы','docs':'документы','planning':'планирование','portfolio':'представление','schema':'данные','stand':'стенд','tests':'проверки','tools':'сборка'}
NAMES = {
 '01-context':'01-контекст','02-requirements':'02-требования','03-architecture':'03-архитектура',
 '04-local-data':'04-дневник-и-расчёты','05-payments':'05-оплата-и-подписка','06-delivery':'06-организация-разработки',
 '07-verification':'07-проверки','08-decisions':'08-решения','09-glossary-sources':'09-словарь-и-источники',
 'workout.schema':'тренировка.схема','workout.example':'тренировка.пример',
 'estimate.schema':'расчёт.схема','estimate.example':'расчёт.пример','requests':'запросы',
 'architecture':'архитектура','server-er':'связи-данных','payment-states':'состояния-платежа',
 'payment-sequence':'последовательность-оплаты','workout-bpmn':'процесс-тренировки','workout':'тренировка',
 'backlog':'список-задач','board':'доска','pages':'страницы','case':'кейс','001-server':'001-сервер','queries':'запросы',
 'api':'сервер','models':'модели','provider':'имитатор','scenario':'сценарий',
 'test_api':'test_сервер','test_auth_edges':'test_вход','test_contracts':'test_контракты','test_local':'test_локальные_данные',
 'assets':'материалы','build':'собрать','check':'проверить',
}

def protocol(value):
    if isinstance(value, dict):
        return {k:protocol(v) for k,v in value.items() if k not in {'title','description','summary','examples','example'}}
    if isinstance(value,list): return [protocol(v) for v in value]
    return value

def main():
    if not (ROOT/'docs').is_dir():
        print('Русская структура уже создана; повторное преобразование не требуется.')
        return
    before = json.loads((ROOT/'contracts/openapi.json').read_text(encoding='utf-8'))
    fingerprint = hashlib.sha256(json.dumps(protocol(before),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    tracked = [ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
    mapping = {}
    for p in tracked:
        rel=p.relative_to(ROOT); parts=list(rel.parts)
        if parts[0] not in DIRS: continue
        parts[0]=DIRS[parts[0]]
        stem=Path(parts[-1]).stem
        parts[-1]=NAMES.get(stem,stem)+Path(parts[-1]).suffix if Path(parts[-1]).suffix else parts[-1]
        if rel.as_posix()=='tools/check.py': parts=['проверки','проверить.py']
        mapping[rel.as_posix()]='/'.join(parts)
    # Сначала полные пути: не заменяем части внешних адресов или имена полей JSON.
    for p in tracked:
        if 'служебное' in p.parts or p.parts[-1]=='check.yml': continue
        try: text=p.read_text(encoding='utf-8')
        except UnicodeDecodeError: continue
        for old,new in sorted(mapping.items(),key=lambda x:-len(x[0])): text=text.replace(old,new)
        for old,new in DIRS.items():
            text=re.sub(r"(['\"])"+re.escape(old)+r"(?=/|['\"])",lambda m:m[1]+new,text)
        for old,new in {'stand.api':'стенд.сервер','stand.models':'стенд.модели','stand.provider':'стенд.имитатор','stand.scenario':'стенд.сценарий','from tools import assets':'from сборка import материалы as assets','from test_api import':'from test_сервер import'}.items(): text=text.replace(old,new)
        # Динамически составляемые имена рисунков и локальные ссылки без папки.
        for old in ('architecture','server-er','payment-states','payment-sequence','workout-bpmn'):
            new=NAMES[old]
            text=re.sub(r"(['\"])"+re.escape(old)+r"(['\"])",lambda m:m[1]+new+m[2],text)
        for old,new in mapping.items():
            if Path(old).parent==p.relative_to(ROOT).parent:
                text=text.replace(']('+Path(old).name+')',']('+Path(new).name+')')
        for old,new in [('case02-board-scenario.json','состояние-доски-кейс-02.json'),('story points','условные оценки трудоёмкости'),('Scrum Master помогает','Специалист по Scrum (Scrum Master) помогает'),('Definition of Done — общие критерии','Общие критерии завершённости (Definition of Done) — критерии'),('Доска Markdown','Доска в GitHub'),('Scrum Guide, HTML','Руководство по Scrum'),('[Scrum Guide]','[Руководство по Scrum]'),('work in progress — начатая незавершённая работа','начатая незавершённая работа'),('Аккаунты, платежи, периоды','Учётные записи, платежи, периоды')]: text=text.replace(old,new)
        if p.suffix=='.md':
            for old,new in [('аккаунтов','учётных записей'),('аккаунта','учётной записи'),('аккаунт','учётная запись'),('провайдера','платёжного сервиса'),('провайдером','платёжным сервисом'),('провайдер','платёжный сервис')]: text=re.sub(r'\b'+old+r'\b',new,text)
        p.write_text(text,encoding='utf-8')
    for old,new in mapping.items():
        target=ROOT/new; target.parent.mkdir(parents=True,exist_ok=True); (ROOT/old).rename(target)
    for old in DIRS:
        for p in sorted((ROOT/old).rglob('*'),reverse=True):
            if p.is_dir(): p.rmdir()
        (ROOT/old).rmdir()
    def patch(path,pairs):
        p=ROOT/path; text=p.read_text(encoding='utf-8')
        for old,new in pairs:
            if old not in text: raise ValueError(f'{path}: исходный фрагмент не найден: {old[:70]}')
            text=text.replace(old,new)
        p.write_text(text,encoding='utf-8')
    patch('compose.yaml', [(", tests]",", проверки]")])
    patch('стенд/Dockerfile', [('COPY stand/requirements.txt','COPY стенд/requirements.txt')]) if 'COPY stand/requirements.txt' in (ROOT/'стенд/Dockerfile').read_text() else None
    # Короткие русские подписи вместо машинных кодов на обзорных схемах.
    patch('сборка/материалы.py', [
      ('accounts\\\\nid PK; email UNIQUE','Учётные записи\\\\naccounts\\\\nКлюч: id; уникальный email'),
      ('sessions\\\\nid PK; account_id FK','Сеансы устройств\\\\nsessions\\\\nКлюч: id; ссылка: account_id'),
      ('payments\\\\nid PK; account_id FK\\\\nUNIQUE(account_id, idempotency_key)','Платежи\\\\npayments\\\\nКлюч: id; ссылка: account_id\\\\nУникальная пара владельца и ключа повтора'),
      ('subscription_periods\\\\npayment_id PK/FK\\\\nstarts_at; ends_at; revoked','Периоды подписки\\\\nsubscription_periods\\\\nКлюч и ссылка: payment_id\\\\nНачало, окончание, отзыв'),
      ('provider_events\\\\nid PK; payment_id FK','Уведомления оплаты\\\\nprovider_events\\\\nКлюч: id; ссылка: payment_id'),
      ('plans\\\\ncode PK; amount_minor\\\\nduration_seconds','Тарифы\\\\nplans\\\\nКлюч: code; цена; длительность'),
      ('challenges\\\\nid PK; email; expires_at\\\\nattempts; used','Запросы кода входа\\\\nchallenges\\\\nКлюч: id; адрес; срок\\\\nПопытки и использование'),
      ('не FK','не внешний ключ'),
      ('creating\\\\nИсход создания неизвестен','Исход создания неизвестен\\\\n(creating)'),
      ('pending\\\\nОплата не подтверждена','Ожидание оплаты\\\\n(pending)'),
      ('succeeded\\\\nУспех подтверждён','Оплата подтверждена\\\\n(succeeded)'),
      ('canceled\\\\nОтмена','Платёж отменён\\\\n(canceled)'),
      ('refunded\\\\nПолный возврат','Полный возврат\\\\n(refunded)'),
      ("'Провайдер'","'Сервис оплаты'"),('participant Провайдер as P','participant "Сервис оплаты" as P'),
      ('Сохранить creating','Сохранить попытку'),("'pending',True","'Ожидает оплаты',True"),
      ('202: paymentId','202: код платежа'),('Доступ до endsAt','Доступ до даты'),
      ('Создать: стабильный ID','Создать: тот же ID'),
    ])
    patch('стенд/сервер.py', [
      ('from stand.models import','from стенд.модели import')
    ]) if 'from stand.models import' in (ROOT/'стенд/сервер.py').read_text() else None
    patch('стенд/сервер.py', [
      ("'message':str(exc.detail)","'message':ERROR_MESSAGES.get(str(exc.detail), 'Не удалось выполнить запрос')"),
      ("app.openapi_version = '3.1.1'", "app.openapi_version = '3.1.1'\nfrom стенд.локализация import ERROR_MESSAGES, localize_openapi\n_original_openapi = app.openapi\napp.openapi = lambda: localize_openapi(_original_openapi())"),
    ])
    patch('стенд/имитатор.py',[("'denied'","'Доступ запрещён'"),("'conflict'","'Повторный запрос содержит другие данные'"),("'not found'","'Платёж не найден'"),("'invalid transition'","'Недопустимое изменение состояния платежа'")])
    patch('стенд/сценарий.py',[("p['status'])","STATUS_LABELS.get(p['status'],p['status']))"),('import httpx','import httpx\nfrom стенд.локализация import STATUS_LABELS')])
    # Документация JSON-схем не изменяет допустимые значения или имена свойств.
    patch('стенд/модели.py', [('from pydantic import BaseModel, ConfigDict, Field, model_validator','from pydantic import BaseModel, ConfigDict, Field, model_validator\nfrom стенд.локализация import localize_schema'),("ConfigDict(extra='forbid')","ConfigDict(extra='forbid', json_schema_extra=localize_schema)")])
    patch('сборка/собрать.py', [
      ('    assets.portfolio()','    assets.portfolio()\n    from стенд.локализация import write_reference\n    write_reference(ROOT)'),
    ])
    # В экспортируемом представлении показываем русское назначение поля, а не голый идентификатор.
    patch('представление/страницы.json', [
      ('тот же paymentId','тот же идентификатор платежа'),
      ('Запись имеет workoutId, revision, время с часовым поясом и единицы измерения.','Запись имеет постоянный идентификатор, номер редакции, время с часовым поясом и единицы измерения.'),
      ('массой на тот момент и methodVersion','массой на тот момент и версией метода'),
      ('сохранением и экспортом','сохранением и выгрузкой'),
    ])
    p=ROOT/'README.md';text=p.read_text(encoding='utf-8')
    text=text.replace('### Практическая проверка','[Русский справочник API и полей](интерфейсы/README.md) · [Обозначения в коде и схемах](документы/10-русские-названия.md)\n\n### Практическая проверка')
    p.write_text(text,encoding='utf-8')
    (ROOT/'проверки/контроль-протокола.json').write_text(json.dumps({'назначение':'Контроль неизменности протокола исходной версии a62f91f без описательных метаданных','sha256':fingerprint},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Переименовано файлов:',len(mapping))
    print('Созданы русские пути; источники схем и PDF переведены; протокол зафиксирован.')

if __name__=='__main__': main()
