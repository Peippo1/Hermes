from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
PROMPTS_DIR = BASE_DIR / "prompts"
DEFAULT_DATA_PATH = OUTPUT_DIR / "sample_accounts.csv"
GENERATED_DIR = OUTPUT_DIR / "generated"


@dataclass(frozen=True)
class AppConfig:
    data_path: Path = Path(os.getenv("HERMES_DATA_PATH", DEFAULT_DATA_PATH))
    generated_dir: Path = GENERATED_DIR
    prompts_dir: Path = PROMPTS_DIR
    use_live_agents: bool = os.getenv("HERMES_USE_LIVE_AGENTS", "false").lower() in {"1", "true", "yes"}
    agent_api_key: str | None = os.getenv("AGENT_API_KEY") or os.getenv("OPENAI_API_KEY")
    app_name: str = "Hermes"


def get_config() -> AppConfig:
    return AppConfig()

