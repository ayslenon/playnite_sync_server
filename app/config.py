from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./game_library.db"
    debug: bool = True
    covers_dir: str = "./playnite_covers"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
