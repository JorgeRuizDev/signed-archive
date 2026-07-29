import time
from typing import Generator


def exponential_backoff(base: float = 2.0, max_retries: int = 3) -> Generator[float, None, None]:
    for i in range(max_retries):
        yield base * (2 ** i)
