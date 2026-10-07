"""Проверяется структура и логика примера, а не физиологическая точность формул."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from stand.models import Workout, Estimate, paid_until, next_period

WORKOUT={'schemaVersion':1,'workoutId':'00000000-0000-4000-8000-000000000001',
 'revision':1,'recordedAt':'2026-10-08T10:00:00+03:00','activity':'walking',
 'environment':'treadmill','durationSeconds':1800,'weightKgAtWorkout':96,
 'segments':[{'durationSeconds':300,'speedKmh':5,'inclinePercent':0},
             {'durationSeconds':1500,'speedKmh':6,'inclinePercent':5}],'actual':True}
ESTIMATE={'calculationId':'00000000-0000-4000-8000-000000000002','workoutId':WORKOUT['workoutId'],
 'sourceRevision':1,'methodVersion':'synthetic-structure-test-1','inputWeightKg':96,
 'activeKcal':100,'restingKcal':20,'totalKcal':120,
 'warning':'Произвольные числа для проверки структуры, не оценка расхода энергии','syntheticFixture':True}

def test_workout_valid():
    assert Workout.model_validate(WORKOUT).durationSeconds==1800

@pytest.mark.parametrize('patch',[{'revision':0},{'durationSeconds':1799},{'actual':False},
 {'recordedAt':'2026-10-08T10:00:00'},{'weightKgAtWorkout':0},{'photo':'base64'},
 {'segments':[]},{'activity':'strength'}])
def test_local_invalid(patch):
    with pytest.raises(ValidationError): Workout.model_validate({**WORKOUT,**patch})

def test_outdoor():
    obj={**WORKOUT,'environment':'outdoor','segments':[],'distanceMeters':2500}
    assert Workout.model_validate(obj).distanceMeters==2500

@pytest.mark.parametrize('patch',[{'distanceMeters':None},{'segments':WORKOUT['segments']}])
def test_outdoor_invalid(patch):
    with pytest.raises(ValidationError):
        Workout.model_validate({**WORKOUT,'environment':'outdoor','segments':[],'distanceMeters':1000,**patch})

def test_estimate_and_profile_change():
    old=Estimate.model_validate(ESTIMATE)
    later={**WORKOUT,'weightKgAtWorkout':90,'revision':2}
    Workout.model_validate(later)
    assert old.inputWeightKg==96 and old.sourceRevision==1

@pytest.mark.parametrize('patch',[{'totalKcal':121},{'activeKcal':-1},{'methodVersion':''}])
def test_estimate_invalid(patch):
    with pytest.raises(ValidationError): Estimate.model_validate({**ESTIMATE,**patch})

def test_expiry_boundary():
    t=datetime(2026,10,8,tzinfo=timezone.utc)
    assert paid_until([(t-timedelta(days=30),t)],t) is None

def test_contiguous_periods():
    t=datetime(2026,10,8,tzinfo=timezone.utc)
    assert paid_until([(t,t+timedelta(days=30)),(t+timedelta(days=30),t+timedelta(days=60))],t)==t+timedelta(days=60)

def test_refund_gap_not_hidden():
    t=datetime(2026,10,8,tzinfo=timezone.utc)
    assert paid_until([(t+timedelta(days=30),t+timedelta(days=60))],t) is None

def test_next_period():
    t=datetime(2026,10,8,tzinfo=timezone.utc)
    assert next_period([(t,t+timedelta(days=30))],t,86400)==(t+timedelta(days=30),t+timedelta(days=31))
