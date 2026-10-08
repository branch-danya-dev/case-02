"""Завершение однократного перевода относительных ссылок и пояснений."""
from pathlib import Path
import json
import re
ROOT=Path(__file__).resolve().parents[1]
NAMES={
 'board.html':'доска.html','board.md':'доска.md','backlog.json':'список-задач.json',
 'case.md':'кейс.md','pages.json':'страницы.json',
 '01-context.md':'01-контекст.md','02-requirements.md':'02-требования.md','03-architecture.md':'03-архитектура.md',
 '04-local-data.md':'04-дневник-и-расчёты.md','05-payments.md':'05-оплата-и-подписка.md',
 '06-delivery.md':'06-организация-разработки.md','07-verification.md':'07-проверки.md',
 '08-decisions.md':'08-решения.md','09-glossary-sources.md':'09-словарь-и-источники.md',
 'architecture.png':'архитектура.png','architecture.svg':'архитектура.svg',
 'server-er.png':'связи-данных.png','server-er.svg':'связи-данных.svg',
 'payment-states.png':'состояния-платежа.png','payment-states.svg':'состояния-платежа.svg',
 'payment-sequence.png':'последовательность-оплаты.png','payment-sequence.svg':'последовательность-оплаты.svg',
 'workout-bpmn.svg':'процесс-тренировки.svg','workout.bpmn':'тренировка.bpmn',
 'workout.schema.json':'тренировка.схема.json','workout.example.json':'тренировка.пример.json',
 'estimate.schema.json':'расчёт.схема.json','estimate.example.json':'расчёт.пример.json',
 'requests.http':'запросы.http','001-server.sql':'001-сервер.sql','queries.sql':'запросы.sql',
}
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ('.git','служебное','__pycache__','.pytest_cache')): continue
    try:text=p.read_text(encoding='utf-8')
    except UnicodeDecodeError:continue
    original=text
    for a,b in NAMES.items():text=text.replace(a,b)
    if p.suffix in ('.md','.json'):
        for a,b in [('Markdown создаются','версия для GitHub создаются'),('HTML и Markdown','интерактивная версия и версия для GitHub'),('Сеанс, token','Сеанс, ключ доступа (token)'),('Product Owner / Scrum Master','Владелец продукта (Product Owner) / специалист по Scrum (Scrum Master)'),('| Backlog |','| Список задач (Backlog) |'),('| Webhook |','| Уведомление (Webhook) |'),('| Definition of Done |','| Критерии завершённости (Definition of Done) |'),('Входящий webhook','Входящее уведомление'),('входящий webhook','входящее уведомление')]:text=text.replace(a,b)
    if p.suffix=='.md':
        for a,b in [('Провайдер','Платёжный сервис'),('провайдеру','платёжному сервису'),('сохраняется creating','сохраняется состояние «исход создания неизвестен» (`creating`)'),('остаётся creating','остаётся состояние «исход создания неизвестен» (`creating`)'),('Состояние creating','Состояние «исход создания неизвестен» (`creating`)')]:text=text.replace(a,b)
        for code,label in {'creating':'Исход создания неизвестен','pending':'Ожидание оплаты','succeeded':'Оплата подтверждена','canceled':'Платёж отменён','refunded':'Полный возврат'}.items():
            text=text.replace('| '+code+' |','| '+label+' (`'+code+'`) |')
    if text!=original:p.write_text(text,encoding='utf-8')

# Название каталога schema переводится, зарезервированный ключ OpenAPI schema — нет.
for name in ('проверки/test_сервер.py','стенд/локализация.py'):
    p=ROOT/name;text=p.read_text(encoding='utf-8')
    text=text.replace("['данные']","['schema']").replace(".get('данные',{})",".get('schema',{})")
    p.write_text(text,encoding='utf-8')
# Проверяем отсутствие именно прежних каталогов, а не переведённых.
p=ROOT/'проверки/test_русификация.py';text=p.read_text(encoding='utf-8')
text=text.replace("for p in ['документы','интерфейсы','схемы','планирование','представление','данные','стенд','проверки','сборка']", "for p in ['docs','contracts','diagrams','planning','portfolio','schema','stand','tests','tools']")
text+='''

def test_parameter_captions_are_russian():
    for item in app.openapi()['paths'].values():
        for operation in item.values():
            if not isinstance(operation,dict): continue
            for parameter in operation.get('parameters',[]):
                name=parameter['name']
                assert name in FIELDS
                assert parameter['schema']['title']==FIELDS[name]
                assert re.search('[А-Яа-яЁё]',parameter['description'])
'''
p.write_text(text,encoding='utf-8')

# Служебный имитатор также показывает понятные подписи и ошибки проверки входных данных.
p=ROOT/'стенд/имитатор.py';text=p.read_text(encoding='utf-8')
text=text.replace("app=FastAPI(title='Имитатор платежей — не настоящая касса')", """app=FastAPI(title='Имитатор платежей — не настоящая касса')
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from стенд.локализация import localize_openapi
_original_openapi=app.openapi
app.openapi=lambda:localize_openapi(_original_openapi())

@app.exception_handler(RequestValidationError)
async def invalid_input(_, exc):
    return JSONResponse(status_code=422,content={'detail':'Проверьте состав и значения полей запроса; лишние поля запрещены'})
""")
for a,b in [
 ("@app.get('/health')","@app.get('/health',summary='Проверить доступность имитатора')"),
 ("@app.post('/payments',dependencies=[Depends(internal)])","@app.post('/payments',dependencies=[Depends(internal)],summary='Создать демонстрационный платёж')"),
 ("@app.get('/payments/{id_}',dependencies=[Depends(internal)])","@app.get('/payments/{id_}',dependencies=[Depends(internal)],summary='Получить сведения о демонстрационном платеже')"),
 ("@app.post('/demo/payments/{id_}',dependencies=[Depends(demo)])","@app.post('/demo/payments/{id_}',dependencies=[Depends(demo)],summary='Изменить исход демонстрационной оплаты')"),
 ("@app.get('/demo/checkout/{id_}')","@app.get('/demo/checkout/{id_}',summary='Открыть пояснение к имитации оплаты')"),
]:text=text.replace(a,b)
p.write_text(text,encoding='utf-8')

# Краткая версия должна объяснять термины без обязательного перехода в полный словарь.
p=ROOT/'представление/страницы.json';pages=json.loads(p.read_text(encoding='utf-8'))
for page in pages:
    for section in page['sections']:
        section['text']=section['text'].replace('контракты API','описания API — программного интерфейса').replace('план Scrum с практиками Kanban','план коротких этапов Scrum с управлением движением задач по Kanban')
pages[-1]['sections'].append({'heading':'Обозначения','text':'API — программный интерфейс; HTTP — протокол запросов и ответов; SQL — язык работы с базой данных. UML — стандарт моделирования систем; BPMN — стандарт описания процессов. Docker Compose совместно запускает компоненты в контейнерах — изолированных окружениях.'})
p.write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Относительные ссылки и названия выгрузок переведены. Зарезервированные ключи протокола сохранены.')
