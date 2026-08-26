"""Central runtime configuration, loaded once from the environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Transcription ---
    transcriber_provider: str = "assemblyai"  # "assemblyai" | "whisper"
    assemblyai_api_key: str = ""

    whisper_model_size: str = "small.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- Reasoning ---
    # Only Groq's gpt-oss models support strict json_schema structured outputs;
    # every other model is limited to json_object (valid JSON, no schema
    # adherence), which defeats the point of a schema-forced citation.
    llm_provider: str = "bedrock"  # "bedrock" | "groq" | "ollama"

    # Claude on AWS Bedrock. Model ids take an "anthropic." prefix here.
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    # OpenAI's open-weight model on Bedrock. Chosen over Claude here for one
    # practical reason: gpt-oss models are auto-enabled for every Bedrock
    # account, while Anthropic models need a use-case form approved first.
    # Swap to a Claude id once that is granted; the Converse call is identical.
    bedrock_model: str = "openai.gpt-oss-120b-1:0"

    # Azure OpenAI. `azure_openai_deployment` is the DEPLOYMENT name you chose
    # in Azure AI Foundry, which is often not the same string as the model name.
    # Structured outputs need a recent api-version; older ones silently fall
    # back to plain JSON, which would break the citation guarantee.
    azure_openai_endpoint: str = ""      # https://<resource>.openai.azure.com
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # --- Storage ---
    database_path: str = "./data/radar.db"
    data_dir: str = "./data"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Evidence verification ---
    evidence_match_threshold: int = 85
    evidence_min_quote_words: int = 5  # short quotes inflate partial_ratio

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
