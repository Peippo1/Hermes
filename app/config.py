from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
PROMPTS_DIR = BASE_DIR / "prompts"
DEFAULT_DATA_PATH = BASE_DIR / "data" / "sample_accounts.csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AppConfig:
    data_path: Path = Path(os.getenv("HERMES_DATA_PATH", DEFAULT_DATA_PATH))
    generated_dir: Path = OUTPUT_DIR
    prompts_dir: Path = PROMPTS_DIR
    use_live_agents: bool = os.getenv("HERMES_USE_LIVE_AGENTS", "false").lower() in {"1", "true", "yes"}
    agent_api_key: str | None = os.getenv("OPENAI_API_KEY") or os.getenv("AGENT_API_KEY")
    model_name: str = os.getenv("HERMES_MODEL", "gpt-4.1-mini")
    cors_origins: str = os.getenv("CORS_ORIGINS", "")
    app_name: str = "Hermes"


def get_config() -> AppConfig:
    return AppConfig()
