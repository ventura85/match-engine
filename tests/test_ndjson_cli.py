from __future__ import annotations
import json
from pathlib import Path
import sys

import main as cli


def test_cli_writes_ndjson(tmp_path):
    # Przygotuj argumenty CLI
    out_path = tmp_path / "events.ndjson"
    argv_bak = sys.argv[:]
    try:
        sys.argv = [
            "prog",
            "--save-json", "false",
            "--save-ndjson", "true",
            "--ndjson-path", str(out_path),
            "--timeline", "last",
            "--timeline-limit", "10",
        ]
        cli.main()
        assert out_path.is_file()
        # Sprawdź kilka pierwszych linii pod kątem poprawnego JSON
        lines = out_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) > 0
        for ln in lines[:5]:
            rec = json.loads(ln)
            assert set(["minute", "type", "team"]).issubset(rec.keys())
            assert isinstance(rec["minute"], int)
            assert isinstance(rec["type"], str)
    finally:
        sys.argv = argv_bak

