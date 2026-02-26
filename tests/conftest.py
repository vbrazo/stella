import os

# Set test environment variables before importing app
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "stella_test")
os.environ.setdefault("WHATSAPP_TOKEN", "test_token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test_phone_id")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test_verify")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("KOMMO_API_TOKEN", "")
os.environ.setdefault("RELEVANCE_AI_API_URL", "")
os.environ.setdefault("RELEVANCE_AI_AUTHORIZATION_TOKEN", "")
