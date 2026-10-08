"""Русские описания без изменения идентификаторов, типов и правил обмена."""
import json
from pathlib import Path

ERROR_MESSAGES = {
 'DEMO_ACCESS_DENIED':'Доступ к служебной операции стенда запрещён',
 'AUTH_REQUIRED':'Для выполнения операции необходимо войти в учётную запись',
 'SESSION_INVALID':'Сеанс отсутствует или истёк; войдите повторно',
 'DEMO_EMAIL_ONLY':'В стенде разрешены только вымышленные адреса с окончанием @example.test',
 'TRY_LATER':'Слишком много запросов кода входа; повторите позднее',
 'CODE_NOT_FOUND':'Код входа не найден в имитаторе почты',
 'CODE_INVALID':'Код неверен, использован или просрочен',
 'PROVIDER_UNAVAILABLE':'Платёжный сервис недоступен; состояние требует повторной сверки',
 'IDEMPOTENCY_CONFLICT':'Этот ключ повтора уже использован для другого тарифа',
 'PLAN_NOT_FOUND':'Указанный тариф не найден',
 'PAYMENT_NOT_FOUND':'Платёж не найден или недоступен этой учётной записи',
 'PROVIDER_PROOF_MISMATCH':'Сведения платёжного сервиса не совпадают с исходным платежом',
 'EVENT_CONFLICT':'Идентификатор уведомления уже относится к другому платежу',
 'PROVIDER_STATUS_INVALID':'Платёжный сервис вернул недопустимое состояние',
 'PROVIDER_ACCESS_DENIED':'Источник платёжного уведомления не прошёл проверку',
 'INVALID_INPUT':'Проверьте состав и значения полей; лишние поля запрещены',
}
STATUS_LABELS={'creating':'Исход создания неизвестен','pending':'Ожидает оплаты','succeeded':'Оплата подтверждена','canceled':'Платёж отменён','refunded':'Полный возврат'}
FIELDS={
 'email':'Адрес электронной почты','code':'Код','message':'Сообщение для пользователя',
 'challengeId':'Идентификатор запроса кода входа','expiresInSeconds':'Срок действия в секундах',
 'deviceLabel':'Название устройства','accountId':'Идентификатор учётной записи',
 'accessToken':'Ключ доступа к сеансу','tokenType':'Способ передачи ключа доступа','expiresAt':'Момент окончания действия',
 'amountMinor':'Сумма в минимальных денежных единицах','currency':'Код валюты',
 'durationSeconds':'Длительность в секундах','automaticRenewal':'Автоматическое продление',
 'planCode':'Код тарифа','paymentId':'Идентификатор платежа','status':'Состояние',
 'checkoutUrl':'Адрес страницы оплаты','eventId':'Идентификатор уведомления','accepted':'Уведомление принято',
 'paid':'Платный доступ действует','activeUntil':'Окончание непрерывного оплаченного периода',
 'features':'Доступные функции','proofKind':'Вид подтверждения доступа',
 'schemaVersion':'Версия формата записи','workoutId':'Идентификатор тренировки','revision':'Номер редакции',
 'recordedAt':'Время записи с часовым поясом','activity':'Вид тренировки','environment':'Условия тренировки',
 'segments':'Отрезки с постоянными параметрами','distanceMeters':'Расстояние в метрах',
 'weightKgAtWorkout':'Масса во время тренировки в килограммах','actual':'Признак фактически выполненной тренировки',
 'speedKmh':'Скорость в километрах в час','inclinePercent':'Уклон в процентах',
 'calculationId':'Идентификатор расчёта','sourceRevision':'Редакция исходной тренировки','methodVersion':'Версия метода расчёта',
 'inputWeightKg':'Масса для расчёта в килограммах','activeKcal':'Активные энергозатраты в килокалориях',
 'restingKcal':'Фоновые энергозатраты в килокалориях','totalKcal':'Общие энергозатраты в килокалориях',
 'warning':'Предупреждение об ограничениях','syntheticFixture':'Признак вымышленного проверочного примера',
 'merchantRef':'Ссылка на платёж продавца','payment_id':'Идентификатор платежа',
 'Idempotency-Key':'Ключ повторяемости запроса','X-Provider-Key':'Ключ проверки платёжного сервиса',
 'detail':'Подробности ошибки','loc':'Расположение ошибочного поля','msg':'Сообщение об ошибке','type':'Вид данных или ошибки',
}
MODELS={'Error':'Ошибка операции','ChallengeIn':'Запрос кода входа','ChallengeOut':'Выданный запрос кода',
 'LoginIn':'Подтверждение входа','SessionOut':'Открытый сеанс','AccountOut':'Учётная запись','Plan':'Тариф',
 'PaymentIn':'Создание оплаты','PaymentOut':'Состояние платежа','Notification':'Платёжное уведомление',
 'Ack':'Подтверждение обработки','Entitlement':'Права доступа','Segment':'Отрезок тренировки',
 'Workout':'Локальная запись тренировки','Estimate':'Результат расчёта','Create':'Создание платежа у имитатора',
 'Change':'Изменение состояния у имитатора','HTTPValidationError':'Ошибка проверки HTTP-запроса','ValidationError':'Ошибка проверки поля'}
ENUMS={**STATUS_LABELS,'walking':'Ходьба','running':'Бег','treadmill':'Беговая дорожка','outdoor':'На улице',
 'Bearer':'Ключ доступа в заголовке Authorization','RUB':'Российский рубль',
 'unsigned-demo':'Демонстрационное подтверждение без криптографической подписи',
 'journal.read':'Чтение дневника','journal.export':'Выгрузка дневника','forecast.advanced':'Расширенный прогноз','body3d.compare':'Сравнение трёхмерных представлений'}

def localize_schema(schema):
    """Изменить только описательные метаданные JSON Schema / OpenAPI."""
    if isinstance(schema,list):
        for value in schema: localize_schema(value)
    elif isinstance(schema,dict):
        for value in list(schema.values()): localize_schema(value)
        title=schema.get('title')
        if title in MODELS: schema['title']=MODELS[title]
        elif isinstance(title,str) and title.startswith('Response '): schema['title']='Ответ операции API'
        for name,field in schema.get('properties',{}).items():
            if name in FIELDS:
                field['title']=FIELDS[name]
                field.setdefault('description',FIELDS[name]+'. Идентификатор поля в формате обмена: '+name+'.')
            values=field.get('enum',[])
            if 'const' in field: values=[field['const']]
            meanings=[str(v)+' — '+ENUMS[v] for v in values if isinstance(v,str) and v in ENUMS]
            if meanings:
                note='Допустимые обозначения: '+'; '.join(meanings)+'.'
                desc=field.get('description','')
                if note not in desc: field['description']=(desc+' '+note).strip()
    return schema

def localize_openapi(spec):
    localize_schema(spec)
    for path in spec.get('paths',{}).values():
        for op in path.values():
            if not isinstance(op,dict): continue
            for code,response in op.get('responses',{}).items():
                response['description']={'200':'Операция выполнена','201':'Запись создана','202':'Запрос принят; результат следует уточнить','204':'Операция выполнена, тело ответа отсутствует','400':'Некорректный запрос','401':'Необходим действующий сеанс','403':'Доступ запрещён','404':'Запись не найдена или недоступна','409':'Конфликт состояния или повторного запроса','422':'Недопустимые входные данные','429':'Превышена частота запросов','503':'Сервис временно недоступен'}.get(code,'Ответ сервера')
            for p in op.get('parameters',[]):
                name=p.get('name','')
                if name in FIELDS:
                    p['description']=FIELDS[name]
                    p.get('schema',{})['title']=FIELDS[name]
    scheme=spec.get('components',{}).get('securitySchemes',{}).get('HTTPBearer')
    if scheme is not None: scheme['description']='Ключ сеанса передаётся в заголовке Authorization: Bearer <ключ>. Значение не публикуется в журнале.'
    return spec

def write_reference(root:Path):
    from стенд.сервер import app
    spec=app.openapi()
    lines=['# Описание API и полей данных','','[Главная страница](../README.md) · [OpenAPI](openapi.json) · [Примеры запросов](запросы.http)','','API — программный интерфейс. HTTP — протокол запросов и ответов. JSON — текстовый формат данных. Имена операций и полей в коде сохранены для совместимости; их назначение приведено по-русски.','','## Операции сервера','','| Метод и адрес | Назначение |','|---|---|']
    for path,item in spec['paths'].items():
        for method,op in item.items():
            if method not in {'get','post','put','patch','delete','head','options'}: continue
            lines.append(f'| `{method.upper()} {path}` | {op.get("summary","")} |')
    lines+=['','## Поля обмена и локальных записей','','Наличие поля в этом словаре не означает, что локальные сведения отправляются на сервер. Тренировки и расчёты описывают отдельные локальные форматы.','','| Идентификатор | Назначение |','|---|---|']
    lines += [f'| `{k}` | {v} |' for k,v in FIELDS.items()]
    lines += ['','Для оплаты `amountMinor` задаётся в копейках при `currency = RUB`. Временные значения передаются с часовым поясом; единицы и ограничения указаны в OpenAPI и схемах.','','## Значения и состояния','','| Код | Значение |','|---|---|']
    lines += [f'| `{k}` | {v} |' for k,v in ENUMS.items()]
    lines += ['','## Ошибки','','Поле `code` предназначено для программной обработки, `message` — для понятного сообщения человеку. Перевод сообщения не изменяет код и HTTP-статус.','','| Код | Сообщение |','|---|---|']
    lines += [f'| `{k}` | {v} |' for k,v in ERROR_MESSAGES.items()]
    lines += ['','## Форматы локальных данных','','[Тренировка: схема](тренировка.схема.json) · [Пример тренировки](тренировка.пример.json) · [Расчёт: схема](расчёт.схема.json) · [Пример расчёта](расчёт.пример.json)','','Фото всегда остаются на устройстве. Эти форматы не добавляют отправку дневника или замеров на сервер.','']
    (root/'интерфейсы/README.md').write_text('\n'.join(lines),encoding='utf-8')
