"""``nbutils.secrets`` -- read credentials without pasting them into notebooks.

Lookup order for ``nbutils.secrets.get(scope, key)``:

1. environment variable ``NBB_SECRET_<SCOPE>_<KEY>`` (upper-cased, other characters -> ``_``),
   e.g. scope ``gemini`` key ``api-key`` -> ``NBB_SECRET_GEMINI_API_KEY``
2. a JSON file ``{"scope": {"key": "value"}}`` at ``$NBBOOST_SECRETS_FILE``
   (default ``~/.nbboost/secrets.json``; keep it ``chmod 600``)

Returned values work like normal strings, but their ``repr`` is ``'[REDACTED]'`` so they are not
echoed by accident. ``print(secret)`` still prints the real value: Jupyter does not scrub output.
"""
from __future__ import annotations

import json
import os
import re
import stat
import warnings
from typing import Dict, List, NamedTuple

ENV_PREFIX = "NBB_SECRET_"
FILE_ENV = "NBBOOST_SECRETS_FILE"
DEFAULT_FILE = "~/.nbboost/secrets.json"


class Secret(str):
    """A string whose repr hides its value."""

    def __repr__(self) -> str:
        return "'[REDACTED]'"

    def _repr_pretty_(self, p, cycle):
        p.text("'[REDACTED]'")


class SecretMetadata(NamedTuple):
    key: str


class SecretScope(NamedTuple):
    name: str


def _norm(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", s).upper()


class Secrets:
    def _file(self) -> str:
        return os.path.expanduser(os.environ.get(FILE_ENV, DEFAULT_FILE))

    def _load_file(self) -> Dict[str, Dict[str, str]]:
        path = self._file()
        if not os.path.exists(path):
            return {}
        try:
            mode = os.stat(path).st_mode
            if mode & (stat.S_IRGRP | stat.S_IROTH):
                warnings.warn(f"{path} is readable by other users; run: chmod 600 {path}", stacklevel=3)
        except OSError:
            pass
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object of scopes")
        return {str(s): {str(k): str(v) for k, v in (kv or {}).items()} for s, kv in data.items()}

    def _env(self) -> Dict[str, Dict[str, str]]:
        """Env secrets can't be split back into scope/key reliably, so they're matched on lookup only."""
        return {k: v for k, v in os.environ.items() if k.startswith(ENV_PREFIX)}

    def get(self, scope: str, key: str) -> Secret:
        env_name = f"{ENV_PREFIX}{_norm(scope)}_{_norm(key)}"
        if env_name in os.environ:
            return Secret(os.environ[env_name])
        val = self._load_file().get(scope, {}).get(key)
        if val is None:
            raise KeyError(f"secret {key!r} not found in scope {scope!r}. "
                           f"Set {env_name} or add it to {self._file()}.")
        return Secret(val)

    def getBytes(self, scope: str, key: str) -> bytes:
        return str(self.get(scope, key)).encode("utf-8")

    def list(self, scope: str) -> List[SecretMetadata]:
        """Key names in a scope (never the values)."""
        keys = set(self._load_file().get(scope, {}))
        prefix = f"{ENV_PREFIX}{_norm(scope)}_"
        keys.update(k[len(prefix):].lower() for k in self._env() if k.startswith(prefix))
        return [SecretMetadata(k) for k in sorted(keys)]

    def listScopes(self) -> List[SecretScope]:
        return [SecretScope(s) for s in sorted(self._load_file())]


secrets = Secrets()
