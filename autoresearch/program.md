# autoresearch-style loop for the WWW 2027 submission

This loop is adapted from karpathy/autoresearch (MIT; inspected at commit `228791f`, 2026-03-25). It reuses the *method*, not the code: one fixed evaluation harness, a narrow set of files the agent may change, objective metrics, keep/discard decided through git, and an untracked results log. The upstream GPT-training code (`train.py`, `prepare.py`, CUDA PyTorch) is not used, because this project trains no models and the host has no NVIDIA GPU.

## The non-negotiable difference from upstream

Upstream optimises `val_bpb` freely. Here, **no empirical result may ever be an optimisation target.** A loop that edits analysis code until an effect size, interval or p-value looks better is a specification search, and it would invalidate the pre-registration (`docs/PRE_ANALYSIS_PLAN.md`, frozen, SHA in `configs/plan_freeze.json`). The gate therefore scores compliance and integrity only.

## Fixed harness (read-only; the equivalent of upstream `prepare.py`)

- `src/www_paper/gate.py`. Run it as `uv run python -m www_paper.gate`. It reports:
  - `tests_pass`: the full suite, with deprecation and future warnings treated as errors;
  - `pdf_built`, `body_pages_le_8`, `total_pages_le_12`, `no_undefined_refs`;
  - `docclass_anonymous_review`;
  - `anonymity_scan_clean`: generic patterns plus the git-ignored `.gate_identity` list;
  - `gate_pass`;
  - advisory metrics: `overfull_boxes`, `first_page_mentions_web`.
- `tests/`, `configs/plan_freeze.json`, `docs/PRE_ANALYSIS_PLAN.md`, `reports/**` (generated evidence) and `paper/generated/**` (regenerated, never hand-edited).

## Files the loop may edit

- **Loop P (presentation).** `paper/main.tex` prose and layout; `src/www_paper/figures.py` styling only (data series stay unchanged).
  - Keep the change if `gate_pass` stays 1 and the targeted reviewer finding is resolved.
  - Otherwise `git reset --hard` to the loop's last kept commit, on the loop branch only.
- **Loop E (engineering).** Performance or clarity changes in `src/www_capacity/*.py` and other pure functions.
  - Keep only if every test passes **and** every regenerated report is byte-identical (`git diff --exit-code reports/ paper/generated/`).
  - Outputs must not change; only speed or simplicity may.
- **Analyses (not a loop).** New analyses are written once, as dated exploratory extensions with their specification fixed before they are run. They are never iterated against their own outcome.

## Loop (bounded; differs from upstream "NEVER STOP")

1. Branch `autoresearch/<tag>` from the current working branch.
2. Make one change, commit it, then run `uv run python -m www_paper.gate > run.log 2>&1` and `grep -E "^(gate_pass|body_pages|tests_summary):" run.log`.
3. Append to `autoresearch/results.tsv` (untracked) the columns `commit`, `gate_pass`, `body_pages`, `status` (`keep`, `discard` or `crash`) and `description`.
4. Keep, or reset to the last kept commit.
5. Stop when the targeted findings list is empty, after 20 iterations, or at a deadline gate in `docs/WWW2027_GOAL.md`, whichever comes first. Then report.

Project rules still apply inside the loop:
- No force-push, merge or external submission without the author's approval.
- No new data provider, purchase or account.
- Credentials are never printed.
- No AI attribution in commits.
