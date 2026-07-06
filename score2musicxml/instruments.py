"""Registry of supported wind instruments.

Each entry maps a CLI-facing instrument id to the music21 instrument class
to use (for correct transposition / MIDI program in the exported MusicXML)
and the clef(s) normally used to write that instrument's part, which is
used only as a sanity-check hint during validation.
"""
from __future__ import annotations

from dataclasses import dataclass

import music21.instrument as m21inst


@dataclass(frozen=True)
class InstrumentSpec:
    id: str
    display_name: str
    m21_class: str
    expected_clefs: tuple[str, ...]

    def make_instrument(self) -> m21inst.Instrument:
        cls = getattr(m21inst, self.m21_class)
        return cls()


_REGISTRY: dict[str, InstrumentSpec] = {}


def _register(id_: str, display_name: str, m21_class: str, expected_clefs: tuple[str, ...]) -> None:
    _REGISTRY[id_] = InstrumentSpec(id_, display_name, m21_class, expected_clefs)


_register("piccolo", "短笛 Piccolo", "Piccolo", ("treble",))
_register("flute", "长笛 Flute", "Flute", ("treble",))
_register("oboe", "双簧管 Oboe", "Oboe", ("treble",))
_register("clarinet_bb", "单簧管(Bb) Clarinet in Bb", "Clarinet", ("treble",))
_register("bass_clarinet", "低音单簧管 Bass Clarinet", "BassClarinet", ("treble", "bass"))
_register("bassoon", "巴松管 Bassoon", "Bassoon", ("bass", "tenor"))
_register("soprano_sax", "高音萨克斯 Soprano Sax", "SopranoSaxophone", ("treble",))
_register("alto_sax", "中音萨克斯 Alto Sax", "AltoSaxophone", ("treble",))
_register("tenor_sax", "次中音萨克斯 Tenor Sax", "TenorSaxophone", ("treble",))
_register("bari_sax", "上低音萨克斯 Baritone Sax", "BaritoneSaxophone", ("treble",))
_register("trumpet_bb", "小号(Bb) Trumpet in Bb", "Trumpet", ("treble",))
_register("horn_f", "圆号(F) Horn in F", "Horn", ("treble",))
_register("trombone", "长号 Trombone (低音谱号/Concert pitch)", "Trombone", ("bass", "tenor"))
_register("bass_trombone", "低音长号 Bass Trombone", "BassTrombone", ("bass",))
_register("euphonium_bc", "上低音号 Euphonium (低音谱号/Concert pitch)", "Baritone", ("bass",))
_register("tuba", "大号 Tuba", "Tuba", ("bass",))


def get(instrument_id: str) -> InstrumentSpec:
    try:
        return _REGISTRY[instrument_id]
    except KeyError as exc:
        raise ValueError(
            f"Unknown instrument id {instrument_id!r}. Available: {', '.join(sorted(_REGISTRY))}"
        ) from exc


def choices() -> list[str]:
    return sorted(_REGISTRY)
