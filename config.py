import os

class Config:
    def __init__(self, env_file: str = ".env"):
        self._load_env_file(env_file)

    def _load_env_file(self, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{path} does not exist.")

        with open(path, "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                os.environ[key] = value
                setattr(self, key, value)  # original case
                setattr(self, key.lower(), value)  # lowercase version
                
config = Config()