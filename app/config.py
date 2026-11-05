from pydantic_settings import BaseSettings
from pathlib import Path
import os

SERVER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = (Path('C:/GameLibraryData/game_library.db') if os.name == 'nt'
                    else Path('/mnt/windows/GameLibraryData/game_library.db'))


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DEFAULT_DATABASE.as_posix()}"
    debug: bool = True
    covers_dir: str = "./app/files"
    frontend_dist: str = str(SERVER_DIR.parent / 'dashboard' / 'dist')
    ssl_certfile: str = "./certs/ayslenon-pc.pem"
    ssl_keyfile: str = "./certs/ayslenon-pc-key.pem"

    model_config = {"env_file": str(SERVER_DIR / '.env'), "env_file_encoding": "utf-8"}


settings = Settings()
