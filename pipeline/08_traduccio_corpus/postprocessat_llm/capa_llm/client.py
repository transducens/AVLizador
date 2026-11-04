"""
llm/client.py -- Client mínim per a Ollama que obliga el model a triar
UNA etiqueta d'una llista tancada. Sense dependències noves (urllib de la
biblioteca estàndard).

Si Ollama no respon, tarda massa o contesta una cosa que no és cap de les
etiquetes, `tria()` torna `None` i la capa deixa la decisió per defecte
del motor: el LLM mai pot inventar text, només triar entre opcions que el
motor ja ha preparat.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

_PARAULA = re.compile(r"[a-zàèéíòóúïüç+]+")


def interpreta(resposta: str, etiquetes: list[str]) -> str | None:
    """Etiqueta triada a partir de la resposta crua del model.

    Prioritat 1: la primera paraula de la resposta (cas normal). Prioritat
    2: si el model s'ha explicat, l'única etiqueta que aparega al text. Si
    no n'hi ha cap o n'hi ha més d'una, `None`.

    >>> interpreta("eixe", ["este", "eixe"])
    'eixe'
    >>> interpreta("  Este.", ["este", "eixe"])
    'este'
    >>> interpreta("Crec que és datiu perquè...", ["datiu", "neutre", "lloc"])
    'datiu'
    >>> interpreta("no ho sé", ["este", "eixe"]) is None
    True
    """
    neta = resposta.strip().lower()
    paraules = _PARAULA.findall(neta)
    if paraules and paraules[0] in etiquetes:
        return paraules[0]
    trobades = [e for e in etiquetes if re.search(rf"(?<![\w+]){re.escape(e)}(?![\w+])", neta)]
    return trobades[0] if len(trobades) == 1 else None


class ClientLLM:
    """Client d'Ollama (`/api/generate`, temperatura 0, sense raonament).

    `model` per defecte `qwen3:8b`, el que va donar el rècord de val->cat
    (129/151, vore `pipeline/08_traduccio_corpus/postprocessat_llm/`).
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
        url: str = "http://localhost:11434",
        timeout: int = 120,
        verbose: bool = False,
    ) -> None:
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.verbose = verbose

    def crida(self, system: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 60},
        }
        peticio = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(peticio, timeout=self.timeout) as resposta:
                text = json.loads(resposta.read().decode("utf-8")).get("response", "")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            text = f"ERROR: {error}"
        if self.verbose:
            print(f"[LLM {self.model}, {time.perf_counter() - t0:.1f}s]\n{prompt}\n-> {text!r}", flush=True)
        return text

    def tria(self, system: str, prompt: str, etiquetes: list[str]) -> tuple[str | None, str]:
        """Torna `(etiqueta o None, resposta crua)`."""
        resposta = self.crida(system, prompt)
        if resposta.startswith("ERROR:"):
            return None, resposta
        return interpreta(resposta, etiquetes), resposta
