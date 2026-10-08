"""Контракты демонстрационного API и локального дневника. Не расчётное ядро приложения."""
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from стенд.локализация import localize_schema

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra=localize_schema)

class Error(Strict):
    code: str
    message: str

class ChallengeIn(Strict):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

class ChallengeOut(Strict):
    challengeId: UUID
    expiresInSeconds: int

class LoginIn(Strict):
    challengeId: UUID
    code: str = Field(pattern=r'^\d{6}$')
    deviceLabel: str = Field(min_length=1, max_length=60)

class SessionOut(Strict):
    accountId: UUID
    accessToken: str
    tokenType: Literal['Bearer'] = 'Bearer'
    expiresAt: datetime

class AccountOut(Strict):
    accountId: UUID
    email: str

class Plan(Strict):
    code: str
    amountMinor: int = Field(gt=0)
    currency: Literal['RUB']
    durationSeconds: int = Field(gt=0)
    automaticRenewal: Literal[False] = False

class PaymentIn(Strict):
    planCode: str = Field(min_length=1, max_length=40)

class PaymentOut(Strict):
    paymentId: UUID
    status: Literal['creating','pending','succeeded','canceled','refunded']
    amountMinor: int
    currency: str
    checkoutUrl: str | None

class Notification(Strict):
    eventId: UUID
    paymentId: UUID

class Ack(Strict):
    accepted: bool = True

class Entitlement(Strict):
    accountId: UUID
    paid: bool
    activeUntil: datetime | None
    features: list[str]
    proofKind: Literal['unsigned-demo'] = 'unsigned-demo'

class Segment(Strict):
    durationSeconds: int = Field(gt=0, le=86400)
    speedKmh: float = Field(gt=0, le=40)
    inclinePercent: float = Field(ge=-30, le=40)

class Workout(Strict):
    schemaVersion: Literal[1] = 1
    workoutId: UUID
    revision: int = Field(ge=1)
    recordedAt: datetime
    activity: Literal['walking','running']
    environment: Literal['treadmill','outdoor']
    durationSeconds: int = Field(gt=0, le=86400)
    segments: list[Segment] = Field(default_factory=list, max_length=1000)
    distanceMeters: float | None = Field(default=None, gt=0)
    weightKgAtWorkout: float = Field(gt=0, le=500)
    actual: Literal[True] = True

    @model_validator(mode='after')
    def consistent(self):
        if self.recordedAt.utcoffset() is None:
            raise ValueError('Нужен часовой пояс события')
        if self.environment == 'treadmill':
            if not self.segments or sum(s.durationSeconds for s in self.segments) != self.durationSeconds:
                raise ValueError('Длительность должна совпадать с суммой отрезков')
        elif self.segments or self.distanceMeters is None:
            raise ValueError('Улица: дистанция обязательна; отрезки дорожки недопустимы')
        return self

class Estimate(Strict):
    calculationId: UUID
    workoutId: UUID
    sourceRevision: int = Field(ge=1)
    methodVersion: str = Field(min_length=1)
    inputWeightKg: float = Field(gt=0)
    activeKcal: float = Field(ge=0)
    restingKcal: float = Field(ge=0)
    totalKcal: float = Field(ge=0)
    warning: str
    syntheticFixture: Literal[True] = True

    @model_validator(mode='after')
    def totals(self):
        if abs(self.activeKcal + self.restingKcal - self.totalKcal) > 0.01:
            raise ValueError('Общие калории не равны сумме активных и фоновых')
        return self

def paid_until(periods, now):
    """Конец непрерывной цепочки оплаченных интервалов, покрывающей now. Разрыв не скрывается."""
    end = now
    for start, stop in sorted(periods):
        if start <= end and stop > end:
            end = stop
    return end if end > now else None

def next_period(periods, now, seconds):
    """Ручная покупка добавляет период после последнего неотозванного периода."""
    start = max([now] + [stop for _, stop in periods])
    return start, start + timedelta(seconds=seconds)
