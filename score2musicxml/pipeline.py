"""End-to-end orchestration: input file -> MusicXML + warnings log."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from music21 import metadata as m21metadata

from . import instruments, merge, postprocess, recognize
from .pdf_to_images import is_pdf, render_pdf_to_images

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass
class PipelineResult:
    musicxml_path: Path
    warnings: list[str]


def resolve_output_dir(output_root: Path, stem: str) -> Path:
    """Pick output_root/stem, or output_root/stem_2, _3, ... if it's taken."""
    candidate = output_root / stem
    n = 2
    while candidate.exists():
        candidate = output_root / f"{stem}_{n}"
        n += 1
    return candidate


def run(
    input_path: Path,
    instrument_id: str,
    output_root: Path,
    *,
    dpi: int = 300,
    debug: bool = False,
) -> PipelineResult:
    spec = instruments.get(instrument_id)
    stem = input_path.stem

    output_dir = resolve_output_dir(output_root, stem)
    work_dir = output_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    if is_pdf(input_path):
        page_images = render_pdf_to_images(input_path, work_dir, dpi=dpi)
    elif input_path.suffix.lower() in IMAGE_SUFFIXES:
        # Copy into work_dir rather than pointing homr at the original file
        # directly: homr always writes its .musicxml output next to whatever
        # image path it's given, which would otherwise litter the user's
        # input folder with a stray file.
        local_copy = work_dir / f"page-0001{input_path.suffix.lower()}"
        shutil.copyfile(input_path, local_copy)
        page_images = [local_copy]
    else:
        raise ValueError(f"Unsupported input type: {input_path.suffix}")

    page_musicxml_paths = [
        recognize.recognize_page(image_path, debug=debug) for image_path in page_images
    ]

    combined_score, merge_warnings = merge.merge_pages(page_musicxml_paths)

    tie_fix_warnings = postprocess.fix_mislabeled_ties(combined_score)
    postprocess.strip_non_essential(combined_score)
    instrument_warnings = postprocess.apply_instrument(combined_score, spec)
    validation_warnings = postprocess.validate(combined_score)

    all_warnings = merge_warnings + tie_fix_warnings + instrument_warnings + validation_warnings

    title = f"{stem}_{instrument_id}"
    combined_score.metadata = combined_score.metadata or m21metadata.Metadata()
    combined_score.metadata.title = title
    combined_score.metadata.composer = ""  # suppress music21's "Music21" placeholder composer

    output_path = output_dir / f"{title}.musicxml"
    # makeNotation=False: don't let music21 "fix" measures whose recognized
    # duration doesn't match the time signature by auto-splitting notes with
    # a tie across the barline - that silently manufactures ties that were
    # never in the source and hides a recognition error we already warn about.
    combined_score.write("musicxml", fp=str(output_path), makeNotation=False)

    return PipelineResult(musicxml_path=output_path, warnings=all_warnings)
