"""gta6-twitch-ccu-forecast-01 forecaster entry point (Python 3.13, standard library only)."""

import json
import os
import sys
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model` finds model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = model.forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
