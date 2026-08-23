"""Central runtime configuration, loaded once from the environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    transcriber_provider: str = "assemblyai"  # "assemblyai" | "whisper"
    assemblyai_api_key: str = ""

    whisper_model_size: str = "small.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct"

    database_path: str = "./data/radar.db"
    data_dir: str = "./data"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    evidence_match_threshold: int = 85

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
