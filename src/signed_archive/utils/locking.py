from contextlib import contextmanager
from pathlib import Path

import portalocker


@contextmanager
def file_lock(lockfile: Path):
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(lockfile, mode="w", flags=portalocker.LOCK_EX | portalocker.LOCK_NB) as fh:
        try:
            yield fh
        finally:
            pass
