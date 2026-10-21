#!/usr/bin/env python3
"""Package only the frontend and verified fixed synthetic fixture for static hosting."""

import argparse
import shutil
import sys
from pathlib import Path

import generate_demo


ROOT = Path(__file__).resolve().parent.parent
FILES = ("index.html", "app.js", "i18n.js", "data/latest.json", "LICENSE")
OUTPUT_FILES = frozenset(FILES + (".nojekyll",))


def build(output):
    for name in FILES + ("data/history.json",):
        source = ROOT / name
        if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(ROOT):
            raise ValueError("Static demo sources must be ordinary files inside this project")
    # A synthetic flag alone is insufficient: reject any changed data, even when
    # marked synthetic, before writing a deployable artifact.
    generate_demo.generate(check=True)
    output = Path(output)
    if output.is_symlink():
        raise ValueError("Static demo output must not be a symbolic link")
    output = output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise ValueError("Static demo output must not replace the source project or its parents")
    if output.exists():
        for existing in output.rglob("*"):
            relative = existing.relative_to(output).as_posix()
            if existing.is_symlink() or (existing.is_dir() and relative != "data") or (
                existing.is_file() and relative not in OUTPUT_FILES
            ):
                raise ValueError("Static demo output contains unexpected files; use a dedicated directory")
    for name in FILES:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (output / ".nojekyll").write_bytes(b"")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "demo")
    args = parser.parse_args(argv)
    try:
        build(args.output)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Static synthetic demo packaged: 6 allowlisted files; no collectors or history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
