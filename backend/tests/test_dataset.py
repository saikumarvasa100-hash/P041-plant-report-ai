"""Dataset pipeline + adaptation interface tests. Provider calls stubbed."""

from app.schemas.analytics import AnalyticsReport
from app.services import llm as llm_mod
from app.services.analytics import analyze_plant
from app.services.dataset import (
    generate_dataset,
    make_training_example,
    validate_training_example,
)
from app.services.grounding import required_numbers
from app.services.model_adaptation import (
    get_training_manifest,
    prepare_training_dataset,
    validate_training_dataset,
)
from app.services.simulator import generate_plant_data


def _stub_provider(monkeypatch, text="Provider-rendered report."):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": text}}]}

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _Resp())


def _analytics():
    return analyze_plant(
        generate_plant_data(num_machines=2, observations_per_machine=8, seed=1)
    )


def _example(seed=7, analytics=None):
    rep = analytics or _analytics()
    target = " ".join(str(v) for _, v in required_numbers(rep))
    return make_training_example(rep, "daily", target, seed=seed)


def test_make_and_validate_example():
    assert validate_training_example(_example()) == []


def test_validate_rejects_bad_example():
    ex = _example()
    ex["report_type"] = "hourly"
    ex["target_report"] = "   "
    problems = validate_training_example(ex)
    assert any("report_type" in p for p in problems)
    assert any("target_report" in p for p in problems)


def test_validate_rejects_tampered_numbers():
    ex = _example()
    ex["target_report"] = "The plant produced 999999 units at 12.5% efficiency."
    assert any("untraceable" in p for p in validate_training_example(ex))


def test_validate_rejects_secrets():
    ex = _example()
    ex["target_report"] += " api_key=sk-abc123"
    assert any("secret" in p for p in validate_training_example(ex))


def test_generate_dataset_uses_provider(monkeypatch):
    _stub_provider(monkeypatch, "Stubbed provider text.")
    from app.core.config import LLMSettings

    settings = LLMSettings(provider="openai-compatible", api_key="k")
    examples = generate_dataset([7], [2], ["daily"], 8, settings)
    assert len(examples) == 1
    assert examples[0]["target_report"] == "Stubbed provider text."
    assert examples[0]["source"] == "synthetic"


def test_adaptation_prepare_and_manifest():
    valid, invalid = prepare_training_dataset([_example(), {"bogus": True}])
    assert len(valid) == 1 and len(invalid) == 1
    manifest = get_training_manifest([_example(), _example(seed=11)])
    assert manifest["num_examples"] == 2
    assert manifest["sources"] == {"synthetic": 2}
    assert "human-reviewed" in manifest["note"]


def test_adaptation_flags_synthetic_only():
    assert any("synthetic-only" in p for p in validate_training_dataset([_example()]))
    assert validate_training_dataset([]) == ["empty dataset"]


def test_example_analytics_roundtrip():
    rep = AnalyticsReport(**_example()["analytics"])
    assert rep.plant.machine_count == 2
