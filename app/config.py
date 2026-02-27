from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WhatsApp provider selection
    whatsapp_provider: str = "cloud_api"  # "cloud_api" | "evolution"

    # WhatsApp Cloud API
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v21.0"

    # Evolution API v2 (only when whatsapp_provider == "evolution")
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance_name: str = ""

    # LLM
    llm_provider: str = "openai"  # "openai" | "anthropic"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "stella"

    # Kommo CRM
    kommo_api_token: str = ""
    kommo_base_url: str = "https://strides.kommo.com"
    kommo_pipeline_id: int = 12571211
    kommo_status_id: int = 97088859

    # LinkedIn Scraper (Relevance AI)
    relevance_ai_api_url: str = ""
    relevance_ai_authorization_token: str = ""

    # Strides API
    strides_api_url: str = "http://localhost:3000"

    # Classifier thresholds
    cluster_confidence_threshold: float = 0.6
    cluster_gap_threshold: float = 0.15

    # Conversation limits
    max_structured_questions: int = 3
    max_questions_with_ambiguity: int = 4

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
