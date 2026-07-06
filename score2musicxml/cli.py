from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import instruments
from .pipeline import IMAGE_SUFFIXES, PipelineResult, run

SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | {".pdf"}


def find_project_root() -> Path:
    """Walk up from the current directory looking for pyproject.toml, so
    input/ and output/ always resolve to the same place regardless of which
    subdirectory the command happens to be run from (e.g. accidentally
    running it from inside input/ used to silently create input/output/).
    """
    here = Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return here


PROJECT_ROOT = find_project_root()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "input"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def resolve_input_path(raw: str) -> Path:
    given = Path(raw)
    if given.exists():
        return given
    candidate = DEFAULT_INPUT_DIR / raw
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Could not find {raw!r} as-is or under {DEFAULT_INPUT_DIR}/. "
        f"Put your PDF/photo in the {DEFAULT_INPUT_DIR}/ folder, or pass a valid path."
    )


def list_batch_inputs() -> list[Path]:
    if not DEFAULT_INPUT_DIR.is_dir():
        return []
    return sorted(
        p for p in DEFAULT_INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )


def print_result(name: str, result: PipelineResult) -> None:
    print(f"Wrote {result.musicxml_path}")
    if result.warnings:
        print(f"  {len(result.warnings)} warning(s) - review these measures in MuseScore:", file=sys.stderr)
        for w in result.warnings:
            print(f"    - {w}", file=sys.stderr)
    else:
        print("  No warnings.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="score2musicxml",
        description=(
            "Recognize a single-part wind instrument score (PDF or image) and export MusicXML. "
            f"Input files are looked up in ./{DEFAULT_INPUT_DIR}/ by default; "
            f"output is written to ./{DEFAULT_OUTPUT_DIR}/<file name>/<file name>_<instrument>.musicxml"
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help=(
            f"Input file name. Looked up under ./{DEFAULT_INPUT_DIR}/ if not found as given. "
            f"Omit to batch-process every PDF/photo currently in ./{DEFAULT_INPUT_DIR}/."
        ),
    )
    parser.add_argument(
        "--instrument",
        required=True,
        choices=instruments.choices(),
        help="Instrument the part is written for (controls transposition/MIDI program in the output). "
        "Applies to every file when batch-processing.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI for PDF input (default: 300)")
    parser.add_argument("--debug", action="store_true", help="Pass --debug through to homr")
    args = parser.parse_args(argv)

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.input is not None:
        input_path = resolve_input_path(args.input)
        result = run(input_path, args.instrument, DEFAULT_OUTPUT_DIR, dpi=args.dpi, debug=args.debug)
        print_result(input_path.name, result)
        return 0

    batch_paths = list_batch_inputs()
    if not batch_paths:
        print(f"No PDF/photo files found in {DEFAULT_INPUT_DIR}/.", file=sys.stderr)
        return 1

    print(f"Batch-processing {len(batch_paths)} file(s) from {DEFAULT_INPUT_DIR}/ as {args.instrument}:\n")
    failures: list[tuple[Path, Exception]] = []
    for input_path in batch_paths:
        print(f"=== {input_path.name} ===")
        try:
            result = run(input_path, args.instrument, DEFAULT_OUTPUT_DIR, dpi=args.dpi, debug=args.debug)
            print_result(input_path.name, result)
        except Exception as exc:  # keep going on a per-file failure
            failures.append((input_path, exc))
            print(f"  FAILED: {exc}", file=sys.stderr)
        print()

    succeeded = len(batch_paths) - len(failures)
    print(f"Done: {succeeded}/{len(batch_paths)} succeeded.")
    if failures:
        print("Failed files:", file=sys.stderr)
        for path, exc in failures:
            print(f"  - {path.name}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
