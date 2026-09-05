# -*- coding: utf-8 -*-
from pathlib import Path
import os

class Settings:
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RAW_DIR: Path = DATA_DIR / "raw"
    SEEDS_DIR: Path = DATA_DIR / "seeds"
    RUNTIME_DIR: Path = DATA_DIR / "runtime"

    # Seed files
    STUDENT_PROFILES_FILE: Path = SEEDS_DIR / "student_profiles.json"
    LEARNING_PATHS_FILE: Path = SEEDS_DIR / "learning_paths.json"
    STUDENT_REPORTS_FILE: Path = SEEDS_DIR / "student_reports.json"
    QUIZ_BANK_FILE: Path = SEEDS_DIR / "quiz_bank.json"
    KNOWLEDGE_GRAPH_FILE: Path = SEEDS_DIR / "knowledge_graph.json"

    # Runtime files
    LEARNING_EVENTS_FILE: Path = RUNTIME_DIR / "learning_events.jsonl"
    BKT_STATES_FILE: Path = RUNTIME_DIR / "bkt_states.json"
    BKT_PROCESSED_EVENTS_FILE: Path = RUNTIME_DIR / "bkt_processed_events.json"
    LEARNING_PATH_STATES_FILE: Path = RUNTIME_DIR / "learning_path_states.json"

    # Raw files
    EXCEL_RAW_FILE: Path = RAW_DIR / "economics_learning_demo.xlsx"

    # Legacy output files fallback (for backward compatibility during migration)
    LEGACY_OUTPUT_DIR: Path = PROJECT_ROOT / "output"

settings = Settings()
