-- Только учёт доступа и оплаты. Тренировок, замеров и фотографий на сервере нет.
CREATE TABLE accounts (
 id uuid PRIMARY KEY,
 email text NOT NULL UNIQUE CHECK (email = lower(email)),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE challenges (
 id uuid PRIMARY KEY,
 email text NOT NULL,
 code_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL,
 attempts smallint NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 5),
 used boolean NOT NULL DEFAULT false
);
CREATE INDEX challenges_email_time ON challenges(email, created_at);
CREATE TABLE sessions (
 id uuid PRIMARY KEY,
 account_id uuid NOT NULL REFERENCES accounts(id),
 token_hash text NOT NULL UNIQUE,
 device_label text NOT NULL,
 expires_at timestamptz NOT NULL
);
CREATE TABLE plans (
 code text PRIMARY KEY,
 amount_minor integer NOT NULL CHECK(amount_minor > 0),
 currency char(3) NOT NULL,
 duration_seconds integer NOT NULL CHECK(duration_seconds > 0)
);
-- Условные цены, не коммерческое предложение. 30 * 24 часа, не календарный месяц.
INSERT INTO plans VALUES ('DEMO-30',29900,'RUB',2592000),('DEMO-60',49900,'RUB',5184000);
CREATE TABLE payments (
 id uuid PRIMARY KEY,
 account_id uuid NOT NULL REFERENCES accounts(id),
 plan_code text NOT NULL REFERENCES plans(code),
 idempotency_key text NOT NULL,
 amount_minor integer NOT NULL CHECK(amount_minor > 0),
 currency char(3) NOT NULL,
 duration_seconds integer NOT NULL CHECK(duration_seconds > 0),
 status text NOT NULL CHECK(status IN ('creating','pending','succeeded','canceled','refunded')),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(account_id,idempotency_key),
 UNIQUE(id,account_id)
);
CREATE TABLE subscription_periods (
 payment_id uuid PRIMARY KEY,
 account_id uuid NOT NULL,
 starts_at timestamptz NOT NULL,
 ends_at timestamptz NOT NULL CHECK(ends_at > starts_at),
 revoked boolean NOT NULL DEFAULT false,
 FOREIGN KEY(payment_id,account_id) REFERENCES payments(id,account_id)
);
CREATE INDEX periods_owner_time ON subscription_periods(account_id,starts_at,ends_at);
CREATE TABLE provider_events (
 id uuid PRIMARY KEY,
 payment_id uuid NOT NULL REFERENCES payments(id),
 received_at timestamptz NOT NULL DEFAULT now()
);
-- Нет данных банковских карт, кода входа в открытом виде и открытых ключей сеансов.
