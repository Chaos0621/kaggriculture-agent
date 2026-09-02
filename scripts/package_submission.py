"""Create submission.tar.gz with main.py at the archive root."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("submission.tar.gz"))
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    main_py = project_root / "main.py"
    if not main_py.is_file():
        raise SystemExit(f"missing submission entry point: {main_py}")

    with tarfile.open(args.output, "w:gz") as archive:
        archive.add(main_py, arcname="main.py")
    print(f"created {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

