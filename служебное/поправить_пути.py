"""Завершение однократного перевода относительных ссылок и пояснений."""
from pathlib import Path
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
    if text!=original:p.write_text(text,encoding='utf-8')
print('Относительные ссылки и названия выгрузок переведены.')
