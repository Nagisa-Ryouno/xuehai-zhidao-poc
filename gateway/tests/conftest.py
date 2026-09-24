# -*- coding: utf-8 -*-
"""
gateway.tests.conftest
======================
Pytest test fixtures ensuring zero test data pollution.
Automatically restores data/ runtime files to their pre-test state upon session completion.
"""

import pytest
from pathlib import Path
from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def preserve_data_directory_isolation():
    """
    Session-wide fixture ensuring no test run permanently mutates data/ files.
    Backs up files that may be written to by integration tests and restores them in teardown.
    """
    data_dir = settings.DATA_DIR
    tracked_files = [
        "companion_events.jsonl",
        "learning_sessions.json",
        "resource_effectiveness_events.jsonl",
        "resource_events.jsonl",
        "learning_events.jsonl",
        "bkt_states.json",
        "bkt_processed_events.json",
        "learning_path_states.json",
    ]
    backups = {}
    for filename in tracked_files:
        f = data_dir / filename
        if f.exists():
            backups[filename] = f.read_bytes()
        else:
            backups[filename] = None

    yield

    # Restore exact state
    for filename, content in backups.items():
        f = data_dir / filename
        if content is None:
            if f.exists():
                f.unlink()
        else:
            f.write_bytes(content)
