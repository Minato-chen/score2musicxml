"""Clean up, validate, and tag the merged score before final export."""
from __future__ import annotations

from music21 import dynamics, expressions, key, meter, note, spanner, stream, tempo, tie as tie_module

from .instruments import InstrumentSpec


def fix_mislabeled_ties(score: stream.Score) -> list[str]:
    """homr sometimes detects a genuine tie (a curve connecting two notes of
    the *same* pitch, with nothing else in between) but emits it as a slur
    instead. Converts those - and only those - to real ties.

    MusicXML only records a slur's two endpoint notes; it does NOT record
    which notes visually fall between them. So a slur whose registered start
    and stop notes happen to share a pitch is not enough to call it a tie -
    if there are other, different-pitch notes physically in between, it's a
    real melodic slur that merely starts and ends on the same pitch. We look
    at every note actually between the two endpoints (in playing order) and
    only convert when *all* of them share that one pitch.
    """
    warnings: list[str] = []
    part = score.parts[0]
    all_notes = list(part.recurse().notes)
    # Index by object identity, not position-by-value: music21 Notes compare
    # equal by pitch/duration/etc., so list.index() can silently match some
    # unrelated earlier note with the same pitch+duration instead of the
    # actual spanner endpoint.
    index_by_id = {id(n): i for i, n in enumerate(all_notes)}

    for sp in list(part.spannerBundle.getByClass(spanner.Slur)):
        endpoints = [n for n in sp.getSpannedElements() if isinstance(n, note.Note)]
        if len(endpoints) < 2:
            continue
        first_note, last_note = endpoints[0], endpoints[-1]
        first_index = index_by_id.get(id(first_note))
        last_index = index_by_id.get(id(last_note))
        if first_index is None or last_index is None:
            continue
        if last_index <= first_index:
            continue

        span_notes = all_notes[first_index : last_index + 1]
        pitches = {n.pitch.nameWithOctave for n in span_notes}
        if len(pitches) != 1:
            continue  # other pitches appear in between - a real slur, leave it alone

        span_notes[0].tie = tie_module.Tie("start")
        for middle in span_notes[1:-1]:
            middle.tie = tie_module.Tie("continue")
        span_notes[-1].tie = tie_module.Tie("stop")

        part.remove(sp)  # spanners live in the stream itself, not just the bundle
        measure = span_notes[0].getContextByClass(stream.Measure)
        warnings.append(
            f"measure {measure.number if measure else '?'}: a same-pitch slur was "
            f"re-labeled as a tie ({pitches.pop()}) - homr likely mis-detected this as a slur"
        )

    return warnings


def strip_non_essential(score: stream.Score) -> None:
    """Remove dynamics, tempo/metronome marks, text expressions, and
    articulations/technical indications in place. Key signature, time
    signature, pitches, durations, and repeat structure are left untouched.
    """
    for el in list(score.recurse()):
        if isinstance(el, (dynamics.Dynamic, tempo.TempoIndication, expressions.TextExpression)):
            site = el.activeSite
            if site is not None:
                site.remove(el)

    for n in score.recurse().notes:
        if getattr(n, "articulations", None):
            n.articulations = []


def apply_instrument(score: stream.Score, spec: InstrumentSpec) -> list[str]:
    """Tag the part with the chosen instrument's name/transposition/MIDI
    program, and sanity-check the recognized clef against what's expected.
    Returns warnings.
    """
    warnings: list[str] = []
    part = score.parts[0]

    for existing in list(part.recurse().getElementsByClass("Instrument")):
        site = existing.activeSite
        if site is not None:
            site.remove(existing)

    instrument_obj = spec.make_instrument()
    part.insert(0, instrument_obj)
    part.partName = instrument_obj.instrumentName
    part.partAbbreviation = instrument_obj.instrumentAbbreviation

    first_measure = next(iter(part.getElementsByClass(stream.Measure)), None)
    if first_measure is not None:
        clefs = list(first_measure.recurse().getElementsByClass("Clef"))
        if clefs:
            recognized_clef_type = clefs[0].sign.lower() if clefs[0].sign else ""
            clef_name_map = {"g": "treble", "f": "bass", "c": "tenor"}
            recognized = clef_name_map.get(recognized_clef_type, recognized_clef_type)
            if recognized not in spec.expected_clefs:
                warnings.append(
                    f"recognized clef '{recognized}' is unusual for {spec.display_name} "
                    f"(expected one of {spec.expected_clefs}) - double check the source pages"
                )

    return warnings


def validate(score: stream.Score) -> list[str]:
    """Check measure durations against the active time signature and log
    any key/time signature changes found. Never auto-corrects anything."""
    warnings: list[str] = []
    part = score.parts[0]

    current_ts: meter.TimeSignature | None = None
    current_ks: key.KeySignature | None = None

    for m in part.getElementsByClass(stream.Measure):
        ts_in_measure = m.getElementsByClass(meter.TimeSignature)
        if ts_in_measure:
            new_ts = ts_in_measure[0]
            if current_ts is not None and new_ts.ratioString != current_ts.ratioString:
                warnings.append(
                    f"measure {m.number}: time signature changed {current_ts.ratioString} -> {new_ts.ratioString}"
                )
            current_ts = new_ts

        ks_in_measure = m.getElementsByClass(key.KeySignature)
        if ks_in_measure:
            new_ks = ks_in_measure[0]
            if current_ks is not None and new_ks.sharps != current_ks.sharps:
                warnings.append(
                    f"measure {m.number}: key signature changed {current_ks.sharps} -> {new_ks.sharps} sharps"
                )
            current_ks = new_ks

        if current_ts is not None:
            expected = current_ts.barDuration.quarterLength
            actual = m.duration.quarterLength
            if abs(actual - expected) > 0.01:
                warnings.append(
                    f"measure {m.number}: duration {actual} does not match time signature "
                    f"{current_ts.ratioString} (expected {expected}) - possible misread note/rest"
                )

    repeat_starts = 0
    repeat_ends = 0
    for m in part.getElementsByClass(stream.Measure):
        if m.leftBarline is not None and m.leftBarline.type == "heavy-light":
            repeat_starts += 1
        if m.rightBarline is not None and getattr(m.rightBarline, "direction", None) == "end":
            repeat_ends += 1
    # A repeat-end with no matching repeat-start is normal notation for
    # "repeat from the top" - only flag a genuine excess of repeat-ends.
    effective_starts = repeat_starts + (1 if repeat_ends > repeat_starts else 0)
    if repeat_ends > effective_starts:
        warnings.append(
            f"repeat barlines look unbalanced: {repeat_starts} explicit start(s) vs {repeat_ends} end(s) - check manually"
        )

    return warnings
