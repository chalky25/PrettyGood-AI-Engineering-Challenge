from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    target_phone_number: str = "+18054398008"
    public_url: str = ""

    deepgram_api_key: str = ""
    groq_api_key: str = ""

    groq_model: str = "llama-3.3-70b-versatile"
    deepgram_stt_model: str = "nova-2"
    deepgram_tts_voice: str = "aura-asteria-en"
    endpointing_ms: int = 900
    max_reply_words: int = 25

    artifacts_dir: str = "artifacts"
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
