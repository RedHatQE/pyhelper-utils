from typing import Optional


class CommandExecFailed(Exception):
    def __init__(self, name: str, err: Optional[str] = None) -> None:
        self.name = name
        self.err = f"Error: {err}" if err else ""

    def __str__(self) -> str:
        return f"Command: {self.name} - exec failed. {self.err}"
