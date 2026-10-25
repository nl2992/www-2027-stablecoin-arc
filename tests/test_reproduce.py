import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEXT = (ROOT / "REPRODUCE.md").read_text()
ENTRY = re.compile(r"def main\(|if __name__ == [\"']__main__[\"']")

# Modules the current paper's pipeline depends on; REPRODUCE.md must name each of them.
REQUIRED = [
    "www_events.acquire", "www_events.bitstamp_hourly", "www_kimchi.download", "www_panel.download",
    "www_auto.probe", "www_auto.harness", "www_auto.record_dev", "www_auto.studies", "www_auto.posthoc_eval",
    "www_auto.robust_eval", "www_auto.td_realdata", "www_auto.anchor", "www_auto.anchor_external",
    "www_auto.noise_bounds", "www_theory.applied", "www_theory.simulate", "www_theory.robustness",
    "www_fuse.panel", "www_fuse.harness", "www_stable.panel", "www_stable.harness",
    "www_q1.panel", "www_q1.gate", "www_q1.run", "www_q2.labels", "www_q2.calibrate", "www_q2.run",
    "www_panel.classify", "www_panel.run", "www_kimchi.analysis",
    "www_rescue.detector_eval", "www_rescue.monitor_sweep", "www_paper.macros", "www_paper.panel_macros",
    "www_paper.q1_macros", "www_paper.q2_macros", "www_paper.bench_macros", "www_paper.figures",
    "www_paper.figures_panel", "www_paper.gate",
]


def _modules() -> list[str]:
    return sorted(set(re.findall(r"python -m ([\w.]+)", TEXT)))


def test_every_module_named_in_reproduce_exists_and_has_an_entry_point():
    modules = _modules()
    assert len(modules) >= 40
    for name in modules:
        spec = importlib.util.find_spec(name)
        assert spec is not None, name
        assert ENTRY.search(Path(spec.origin).read_text()), f"{name} has no CLI entry point"


def test_reproduce_names_every_module_of_the_current_pipeline():
    named = set(_modules())
    missing = [m for m in REQUIRED if m not in named]
    assert not missing, f"REPRODUCE.md does not name: {missing}"


def test_input_files_named_in_reproduce_exist():
    paths = set(re.findall(r"(?:configs|docs|src|tests|resource)/[\w./-]+\.(?:json|md|py|yaml)", TEXT))
    paths |= set(re.findall(r"autoresearch/(?:program[\w]*\.md|final_[\w]+\.log|results_[\w]+_run1\.tsv)", TEXT))
    assert len(paths) >= 15
    missing = sorted(p for p in paths if "*" not in p and not (ROOT / p).exists())
    assert not missing, missing


def test_reproduce_and_readme_hold_no_key_values():
    for name in ("REPRODUCE.md", "README.md"):
        text = (ROOT / name).read_text()
        assert not re.search(r"FRED_API_KEY=\s*[0-9a-fA-F]{16,}", text), name
        assert not re.search(r"\b[0-9a-f]{32}\b", text), name  # a bare 32-hex string looks like an API key
        assert not re.search(r"https?://[^\s)]*(alchemy|infura)[^\s)]*/v2/", text), name


def test_reproduce_hashes_match_recorded_provenance():
    freeze_anchor = (ROOT / "configs/event_registry.json").read_text()
    assert "17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3" in TEXT and \
        "17704ff01a86c3c678c690aeb7b9a9f2a86702bd69bbe5cceaf359c68c6711b3" in freeze_anchor
    c1 = (ROOT / "reports/c1/march01_sample_validation.json").read_text()
    sha = "2061a9ff9898b24900692aae31d9c98cd547aa7e815223329b37a0834ebd8511"
    assert sha in TEXT and sha in c1
    kraken = "bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7"
    assert kraken in TEXT and kraken in (ROOT / "reports/events/acquisition_manifest.json").read_text()


def test_locked_steps_are_listed_with_their_unlock_files_and_logs():
    for token in ("FINAL_UNLOCK", "FINAL_UNLOCK_FUSE", "FINAL_UNLOCK_STABLE", "final_test_724455b.log",
                  "final_fuse_914b3cb.log", "final_stable_ca38772.log", "program_q1.md", "program_q2.md",
                  "program_panel.md", "Q2_CALIBRATION_CHANGE.md"):
        assert token in TEXT, token
