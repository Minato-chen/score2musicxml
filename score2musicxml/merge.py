"""Stitch per-page homr MusicXML output into one continuous single-voice part."""
from __future__ import annotations

import copy
from pathlib import Path

from music21 import clef, converter, stream


def merge_pages(musicxml_paths: list[Path]) -> tuple[stream.Score, list[str]]:
    """Concatenate the measures from each page's recognized MusicXML, in order.

    Returns (combined_score, warnings). Each page is expected to contain a
    single monophonic part; if homr emits more than one part for a page
    (unexpected for our target input) we take the first and warn.
    """
    warnings: list[str] = []
    combined_part = stream.Part()
    measure_counter = 0

    for page_index, path in enumerate(musicxml_paths, start=1):
        page_score = converter.parse(path)
        page_parts = list(page_score.parts)

        if not page_parts:
            warnings.append(f"page {page_index}: no parts found in {path.name}, skipped")
            continue
        if len(page_parts) > 1:
            warnings.append(
                f"page {page_index}: expected 1 part but homr found {len(page_parts)}; "
                "using the first one (page may contain more than one staff/instrument)"
            )
        source_part = page_parts[0]

        # Deep-copy the whole page part in one shot (not measure-by-measure):
        # slurs and other spanners live in the part's spannerBundle and point
        # at specific Note objects, so copying measures individually would
        # silently drop every slur (their target notes would live in a
        # different copy than the spanner).
        copied_part = copy.deepcopy(source_part)

        measures = list(copied_part.getElementsByClass(stream.Measure))
        if not measures:
            warnings.append(f"page {page_index}: no measures recognized in {path.name}")
            continue

        for m in measures:
            measure_counter += 1
            m.number = measure_counter
            combined_part.append(m)

        for sp in copied_part.spannerBundle:
            combined_part.insert(0, sp)

    combined_score = stream.Score()
    combined_score.insert(0, combined_part)

    _dedupe_redundant_clefs(combined_part, warnings)
    return combined_score, warnings


def _dedupe_redundant_clefs(part: stream.Part, warnings: list[str]) -> None:
    """homr emits a clef at the top of every page; keep only the first occurrence
    unless the clef genuinely changes, to avoid clutter in the merged score."""
    last_clef_name: str | None = None
    for m in part.getElementsByClass(stream.Measure):
        clefs = list(m.getElementsByClass(clef.Clef))
        if not clefs:
            continue
        this_clef_name = clefs[0].name
        if last_clef_name is not None and this_clef_name == last_clef_name and m.number != 1:
            m.remove(clefs[0])
        elif last_clef_name is not None and this_clef_name != last_clef_name:
            warnings.append(f"measure {m.number}: clef changed to {this_clef_name} (check this is real, not a mis-read)")
        last_clef_name = this_clef_name
