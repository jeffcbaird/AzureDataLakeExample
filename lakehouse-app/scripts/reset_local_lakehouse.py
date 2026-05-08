"""
Wipe local silver/, gold/, quarantine/, dq_results/ for a clean run.
Bronze is preserved so you don't need to re-seed.

Run: make reset  OR  ENV=local python scripts/reset_local_lakehouse.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lakehouse_common.config.settings import Settings

settings = Settings()


def main() -> None:
    targets = [
        Path(settings.silver_path()),
        Path(settings.gold_path()),
        Path(settings.quarantine_path()),
        Path(settings.dq_results_path()),
    ]
    for t in targets:
        if t.exists():
            shutil.rmtree(t)
            print(f"  removed {t}")
        else:
            print(f"  skipped {t} (does not exist)")
    print("Reset complete. Bronze data preserved.")


if __name__ == "__main__":
    main()
