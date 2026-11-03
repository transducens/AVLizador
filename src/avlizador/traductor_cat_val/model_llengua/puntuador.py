"""
model_llengua/puntuador.py -- Probabilitat d'un text segons un model de
llengua causal (`transformers`, en CPU). Dependència opcional: `torch` i
`transformers` només s'importen en crear un `ModelLlengua`.

`logprob(text)` = suma de log P(token | tokens d'abans) de tot el text,
començant pel token d'inici. Quant més alta (menys negativa), més
"normal" li sembla la frase al model. Es guarda en memòria cau: el mateix
text no es calcula dos voltes.

Context valencià (03/11/2026): per defecte cada text es puntua com a
continuació de `CONTEXT_PER_DEFECTE`, un paràgraf curt en valencià:
log P(text | context). FLOR-760M té biaix cap a la forma més freqüent en
el seu corpus (la catalana: "vegada" davant de "colp", "rentadora" davant
de "llavadora"); el paràgraf davant el posa "en mode valencià". Proves en
`pipeline/03_seleccio_de_model/model_llengua/sesgo/` (paràgraf P1):
paraules ambigües encertades 83 -> 90/101 (homògrafs v1) i 113 -> 124/161
(v2), el manual igual (33/34). El context passa pel model una sola vegada
(se'n guarden els `past_key_values`): no alenteix la puntuació.
`context=None` torna al comportament d'abans.
"""

from __future__ import annotations

import copy

MODEL_PER_DEFECTE = "projecte-aina/FLOR-760M"
MODELS_PROVATS = ("projecte-aina/FLOR-760M", "BSC-LT/salamandra-2b")
CONTEXT_PER_DEFECTE = (
    "Este és un text escrit en valencià. Hui els xiquets han eixit prompte de l'escola "
    "i se n'han anat a casa per a vore la seua família."
)


class ModelLlengua:
    def __init__(self, model_id: str = MODEL_PER_DEFECTE, fils: int | None = None, dtype: str = "bfloat16",
                 context: str | None = CONTEXT_PER_DEFECTE):
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
        self.context = context
        if context:
            self._ids_context = [self.bos] + self.tok(context, add_special_tokens=False)["input_ids"]
            with torch.no_grad():
                eixida = self.lm(torch.tensor([self._ids_context]), use_cache=True)
            self._kv_context = eixida.past_key_values
            self._ultim_context = eixida.logits[0, -1].float()

    def _logprob_sense_context(self, ids: list[int]) -> float:
        torch = self._torch
        x = torch.tensor([ids])
        with torch.no_grad():
            lp = torch.log_softmax(self.lm(x).logits[0, :-1].float(), -1)
        return lp[torch.arange(len(ids) - 1), x[0, 1:]].sum().item()

    def _logprob_amb_context(self, text: str) -> tuple[float, int]:
        """log P(text | context): només es calculen els tokens del text, sobre
        els `past_key_values` del context. Si el tokenitzador no talla el
        context igual dins de "context + text", es calcula tot sencer
        (log P(context + text) − log P(context), el mateix valor)."""
        torch = self._torch
        ids = [self.bos] + self.tok(self.context + " " + text, add_special_tokens=False)["input_ids"]
        n_c = len(self._ids_context)
        if ids[:n_c] != self._ids_context:
            return (self._logprob_sense_context(ids) - self._logprob_sense_context(self._ids_context),
                    len(ids) - n_c)
        nous = ids[n_c:]
        with torch.no_grad():
            eixida = self.lm(torch.tensor([nous]), past_key_values=copy.deepcopy(self._kv_context),
                             use_cache=True, attention_mask=torch.ones(1, len(ids), dtype=torch.long))
        logits = torch.cat([self._ultim_context[None], eixida.logits[0, :-1].float()])
        lp = torch.log_softmax(logits, -1)[torch.arange(len(nous)), torch.tensor(nous)].sum().item()
        return lp, len(nous)

    def logprob(self, text: str) -> tuple[float, int]:
        """`(suma de log-probabilitats, nombre de tokens)` de `text` (amb el
        context davant, si n'hi ha)."""
        if text not in self._cache:
            if self.context:
                self._cache[text] = self._logprob_amb_context(text)
            else:
                ids = [self.bos] + self.tok(text, add_special_tokens=False)["input_ids"]
                self._cache[text] = (self._logprob_sense_context(ids), len(ids) - 1)
        return self._cache[text]
