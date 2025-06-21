
from dataclasses import dataclass


@dataclass
class Providers:
    GPT = "gpt"
    DALLE = "dalle"
    UNKNOWN = "unknown"

