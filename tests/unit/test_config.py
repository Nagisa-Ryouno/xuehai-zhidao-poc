# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
from app.core.config import settings
from app.core.constants import DEFAULT_BKT_PARAMS, PathState

class TestCoreConfig(unittest.TestCase):
    def test_settings_paths_resolve_to_project_root(self):
        self.assertTrue(settings.PROJECT_ROOT.exists())
        self.assertEqual(settings.DATA_DIR, settings.PROJECT_ROOT / "data")
        self.assertEqual(settings.SEEDS_DIR, settings.DATA_DIR / "seeds")
        self.assertEqual(settings.RUNTIME_DIR, settings.DATA_DIR / "runtime")
        self.assertEqual(settings.RAW_DIR, settings.DATA_DIR / "raw")

    def test_bkt_constants_frozen(self):
        self.assertEqual(DEFAULT_BKT_PARAMS.p_init, 0.20)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_transit, 0.10)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_guess, 0.20)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_slip, 0.10)
