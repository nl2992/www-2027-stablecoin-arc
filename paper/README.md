# Manuscript (provisional draft)

- `main.tex` uses ACM `acmart` (`sigconf,review,anonymous`). Compiling needs a TeX distribution that provides `acmart`. **No TeX toolchain is installed on the authoring machine, so the PDF build has not been verified.**
- Every empirical number is a `\Num...` macro in `generated/numbers.tex`. Regenerate it with `uv run python -m www_paper.macros`. Each macro line names its source report and JSON path.
- `tests/test_paper.py` fails if the generated numbers are stale, if a macro is undefined, if a bps or percent value is typed by hand (other than pre-specified design constants), if a citation lacks a bib entry, or if a bib entry is unused.
- `references.bib` holds only entries verified on 2026-10-11. Sections marked `[PENDING]` must not be filled with unmeasured values.
