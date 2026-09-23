"""
repara_preambul.py -- Aplica em.neteja_preambul() a un corpus_*.jsonl ya
generado, para casos como salamandra-7b-instruct que anteponia "Resposta
correcta:" a cada traduccion porque genera_corpus_sintetico.py no llamaba
a esa limpieza (bug real, ya corregido en el script para futuras
generaciones -- esto es solo para arreglar lo que ya tienes).

US:
    python repara_preambul.py ruta/al/corpus_salamandra.jsonl
    (sobreescribe el mismo fichero; guarda cuantas lineas cambiaron)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_seleccion_de_modelo"))
import evalua_models as em


def main():
    if len(sys.argv) != 2:
        print("Uso: python repara_preambul.py ruta/al/corpus.jsonl")
        sys.exit(1)

    ruta = Path(sys.argv[1])
    registres = []
    canviats = 0
    with open(ruta, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if not linia:
                continue
            r = json.loads(linia)
            net = em.neteja_preambul(r.get("frase_cat", ""))
            if net != r.get("frase_cat", ""):
                canviats += 1
                r["frase_cat"] = net
            registres.append(r)

    with open(ruta, "w", encoding="utf-8") as f:
        for r in registres:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Revisadas {len(registres)} frases, {canviats} tenian preambulo fugado -- arregladas.")


if __name__ == "__main__":
    main()
