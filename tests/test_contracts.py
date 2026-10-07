from pathlib import Path
import json
from openapi_spec_validator import validate_spec
from pydantic import ValidationError
from stand.api import app
from stand.models import Workout, Estimate
ROOT=Path(__file__).resolve().parents[1]

def test_openapi_valid_and_current():
    saved=json.loads((ROOT/'contracts/openapi.json').read_text(encoding='utf-8'))
    validate_spec(saved)
    assert saved==app.openapi()
    assert not any('/demo/' in p for p in saved['paths'])

def test_example_links():
    w=Workout.model_validate_json((ROOT/'contracts/workout.example.json').read_text(encoding='utf-8'))
    e=Estimate.model_validate_json((ROOT/'contracts/estimate.example.json').read_text(encoding='utf-8'))
    assert e.workoutId==w.workoutId and e.sourceRevision==w.revision
    assert e.inputWeightKg==w.weightKgAtWorkout
