from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KG_")

    data_dir: str = "/data"
    validation_mode: str = "warn"  # warn | error
    ontology_graph: str = "urn:kg:ontology"
    data_graph: str = "urn:kg:data"
    kg_namespace: str = "urn:kg:"
    cors_origins: list[str] = Field(
        default=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        ]
    )


settings = Settings()
