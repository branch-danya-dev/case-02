# 07. Проверка, прослеживаемость и ограничения доказательства

[Главная страница](../README.md) · [Стенд](../stand/README.md) · [Автоматические запуски](https://github.com/branch-danya-dev/case-02/actions)

## Требование → материал → проверка

| Требования | Материалы | Исполняемые проверки |
|---|---|---|
| ФТ-01–02 | POST challenges/sessions; SQL challenges/sessions | test_code_single_use_and_attempt_limit, test_rate_limit, test_registration_second_device_and_logout |
| ФТ-03–04 | POST payments; UNIQUE(account_id,idempotency_key) | test_idempotency_replay_and_conflict, test_concurrent_create_single_payment, test_server_rejects_unexpected_fields |
| ФТ-05–06 | Уведомление, доверенная сверка, SQL periods/events | test_pending_does_not_grant_access, test_notification_auth_and_unconfirmed_provider, test_success_duplicate_different_event_second_device, test_concurrent_notifications_single_period |
| ФТ-07 | Состояние creating и стабильный ключ внешней операции | test_provider_timeout_keeps_same_payment |
| ФТ-08–09 | GET entitlements, границы периодов, отзыв | test_expiry_boundary, test_contiguous_periods, test_refund_gap_not_hidden, test_refund_does_not_resurrect_access |
| ФТ-10 | Проверка владельца по сеансу | test_isolation |
| ФТ-11–12 | Локальные Workout/Estimate и схемы JSON | test_workout_valid, test_local_invalid, test_outdoor, test_estimate_and_profile_change, test_estimate_invalid, test_example_links |
| ФТ-13 | Строгие модели API, отсутствие методов передачи дневника | test_server_rejects_unexpected_fields, test_no_photo_or_journal_endpoint |
| ФТ-15 | Повторная сверка | test_missing_notification_reconciled |
| НТ-02 | Транзакции и уникальные ограничения PostgreSQL | test_concurrent_notifications_single_period, test_sql_integrity |

Тесты находятся в [tests/test_api.py](../tests/test_api.py), [tests/test_local.py](../tests/test_local.py), [tests/test_contracts.py](../tests/test_contracts.py). OpenAPI проверяется валидатором и сравнением с описанием исполняемой модели. Ответы выбранных сценариев сверяются со схемой, не только с кодом HTTP.

## Проверки, которые остаются постановкой, а не выполненным результатом

ФТ-14: интеграция расчёт → существующая 3D-модель, визуальная корректность и научная оценка прогноза. ФТ-16: реальное сохранение в браузере, нехватка места, обновление формата и восстановление. НТ-01: сетевой аудит всего исходного приложения. Защищённое автономное разрешение, доставка кодов, промышленная касса, нагрузка и доступность также не реализованы.

Схемы ограничивают формат, а межполевые равенства дополнительно проверяются моделью. JSON Schema сама по себе не проверяет равенство суммы отрезков и durationSeconds. Научная точность калорий не проверяется произвольными числами примера.

## Ручные условия приёмки будущего приложения

1. Записать тренировку без сети, перезапустить клиент и открыть ту же запись. Успех только после фактического сохранения.
2. Изменить массу в профиле: прежний расчёт не меняется. Явный пересчёт создаёт новую версию результата.
3. Войти на другом устройстве: права подписки совпадают, дневник автоматически не появляется.
4. Отключить передачу данных: исходящих запросов с дневником нет. Фотографии не передаются ни в одном режиме.
5. После конца подписки прочитать и выгрузить записи. Изображение прогноза остаётся подписано как прогноз.

## Как воспроизвести проверку

```bash
docker compose up --build -d --wait
docker compose --profile test run --rm tests
```

Число тестов и результат конкретного запуска смотрите в GitHub Actions. Оно не равно числу полностью реализованных функций продукта. Для технического разбора сначала запускается один [показательный сценарий](../stand/scenario.py), затем разбираются его правила и негативные проверки.
