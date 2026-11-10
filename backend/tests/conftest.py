from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_ROOT = Path(__file__).resolve().parent / ".runtime"
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
TEST_ROOT.mkdir(parents=True)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_ROOT / 'test.db'}")
os.environ.setdefault("UPLOAD_DIR", str(TEST_ROOT / "uploads"))
os.environ.setdefault("ANNOTATED_DIR", str(TEST_ROOT / "annotated"))
os.environ.setdefault("MODEL_MODE", "cv_demo")
