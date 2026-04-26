from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator
from unittest.mock import patch


TEST_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_accounts.csv"
TEST_ENV_KEYS = (
    "HERMES_DATA_PATH",
    "HERMES_GOOGLE_SHEET_CSV_URL",
    "HERMES_USE_LIVE_AGENTS",
    "OPENAI_API_KEY",
    "AGENT_API_KEY",
)


@contextmanager
def deterministic_test_env() -> Iterator[None]:
    saved_values = {key: os.environ.get(key) for key in TEST_ENV_KEYS}
    try:
        os.environ["HERMES_DATA_PATH"] = str(TEST_DATA_PATH)
        os.environ.pop("HERMES_GOOGLE_SHEET_CSV_URL", None)
        os.environ["HERMES_USE_LIVE_AGENTS"] = "false"
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("AGENT_API_KEY", None)
        yield
    finally:
        for key, value in saved_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def load_test_app_module() -> ModuleType:
    with deterministic_test_env(), patch("dotenv.load_dotenv", return_value=None):
        config_module = sys.modules.get("app.config")
        if config_module is None:
            config_module = importlib.import_module("app.config")
        else:
            config_module = importlib.reload(config_module)

        main_module = sys.modules.get("app.main")
        if main_module is None:
            main_module = importlib.import_module("app.main")
        else:
            main_module = importlib.reload(main_module)

    return main_module
