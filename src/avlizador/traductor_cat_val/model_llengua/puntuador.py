"""
model_llengua/puntuador.py -- Probabilitat d'un text segons un model de
llengua causal (`transformers`, en CPU). Dependència opcional: `torch` i
`transformers` només s'importen en crear un `ModelLlengua`.

`logprob(text)` = suma de log P(token | tokens d'abans) de tot el text,
començant pel token d'inici. Quant més alta (menys negativa), més
"normal" li sembla la frase al model. Es guarda en memòria cau: el mateix
text no es calcula dos voltes.
"""

from __future__ import annotations

MODEL_PER_DEFECTE = "projecte-aina/FLOR-760M"
MODELS_PROVATS = ("projecte-aina/FLOR-760M", "BSC-LT/salamandra-2b")


class ModelLlengua:
    def __init__(self, model_id: str = MODEL_PER_DEFECTE, fils: int | None = None, dtype: str = "bfloat16"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if fils:
            torch.set_num_threads(fils)
        self._torch = torch
        self.model_id = model_id
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.lm = AutoModelForCausalLM.from_pretrained(model_id, dtype=getattr(torch, dtype))
        self.lm.eval()
        self.bos = self.tok.bos_token_id if self.tok.bos_token_id is not None else self.tok.eos_token_id
        self._cache: dict[str, tuple[float, int]] = {}

    def logprob(self, text: str) -> tuple[float, int]:
        """`(suma de log-probabilitats, nombre de tokens)` de `text`."""
        if text not in self._cache:
            torch = self._torch
            ids = [self.bos] + self.tok(text, add_special_tokens=False)["input_ids"]
            x = torch.tensor([ids])
            with torch.no_grad():
                lp = torch.log_softmax(self.lm(x).logits[0, :-1].float(), -1)
            self._cache[text] = (lp[torch.arange(len(ids) - 1), x[0, 1:]].sum().item(), len(ids) - 1)
        return self._cache[text]
