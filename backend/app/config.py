from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="KG_")

    data_dir: str = "/data"
    validation_mode: str = "warn"  # warn | error
    ontology_graph: str = "urn:kg:ontology"
    data_graph: str = "urn:kg:data"
    kg_namespace: str = "urn:kg:"


settings = Settings()
