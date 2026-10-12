import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_every_module_named_in_reproduce_exists_and_has_a_main():
    text = (ROOT / "REPRODUCE.md").read_text()
    modules = sorted(set(re.findall(r"python -m ([\w.]+)", text)))
    assert len(modules) >= 10
    for name in modules:
        spec = importlib.util.find_spec(name)
        assert spec is not None, name
        assert "def main(" in Path(spec.origin).read_text(), f"{name} has no CLI entry point"


def test_reproduce_hashes_match_recorded_provenance():
    text = (ROOT / "REPRODUCE.md").read_text()
    freeze_anchor = (ROOT / "configs/event_registry.json").read_text()
    assert "17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3" in text and \
        "17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3" in freeze_anchor
    c1 = (ROOT / "reports/c1/march01_sample_validation.json").read_text()
    sha = "2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511"
    assert sha in text and sha in c1
