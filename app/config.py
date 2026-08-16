from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./game_library.db"
    debug: bool = True
    covers_dir: str = "./app/files"
    frontend_dist: str = "../dashboard/dist"
    ssl_certfile: str = "./certs/ayslenon-pc.pem"
    ssl_keyfile: str = "./certs/ayslenon-pc-key.pem"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
