from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="auth/.env",
        env_file_encoding="utf-8",
    )

    database_url : str

    secret_key: SecretStr
    # blogger account
    #  going to  get values from .env file.  Notice in both  files,  the names  are same but DIFFER in case.
    #  the existing value system environment variable  gets higher priority than .env file.

    

    s3_bucket_name: str
    s3_region: str = "us-east-2"
    s3_access_key: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    # reason why key are optional, if the project is run from within EC2 instance, then key values are not requred, the aws identity running the EC2 will be applied.


    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # while writing the image handles...
    max_upload_size_bytes: int = 5 * 1024 *1024

    posts_per_page: int = 3

settings = Settings()
