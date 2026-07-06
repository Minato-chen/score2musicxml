"""Run the homr OMR engine on a single page image."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class RecognitionError(RuntimeError):
    pass


def recognize_page(image_path: Path, *, debug: bool = False) -> Path:
    """Run homr on image_path, returning the path to the .musicxml it writes.

    homr always writes its output next to the input image, named
    "<image_stem>.musicxml" (see homr/main.py: replace_extension).
    """
    expected_output = image_path.with_suffix(".musicxml")

    homr_bin = Path(sys.executable).with_name("homr")
    cmd = [str(homr_bin), str(image_path)]
    if debug:
        cmd.append("--debug")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RecognitionError(
            f"homr failed on {image_path} (exit {result.returncode}):\n{result.stderr}"
        )
    if not expected_output.exists():
        raise RecognitionError(
            f"homr reported success but no output found at {expected_output}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return expected_output
