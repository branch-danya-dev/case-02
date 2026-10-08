-- Платежи, которые требуют повторной сверки с внешней системой.
SELECT id, account_id, status, created_at
FROM payments WHERE status IN ('creating','pending') ORDER BY created_at;

-- Контроль: подтверждённые платежи без периода доступа. Норма: пустой результат.
SELECT p.id FROM payments p
LEFT JOIN subscription_periods s ON s.payment_id=p.id
WHERE p.status='succeeded' AND s.payment_id IS NULL;

-- Контроль: возврат денег не должен оставлять действующий период этого платежа.
SELECT p.id FROM payments p
JOIN subscription_periods s ON s.payment_id=p.id
WHERE p.status='refunded' AND NOT s.revoked;

-- Пример отчёта без тренировок и замеров: количество платежей по состоянию.
SELECT status, count(*) FROM payments GROUP BY status ORDER BY status;
