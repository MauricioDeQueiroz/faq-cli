"""Comparação RAG x CAG (Checkpoint B).

Uso: python avaliar_comparacao.py

Roda as mesmas 10 perguntas de teste em dois modos (RAG e CAG), medindo:
  - latência por pergunta (segundos)
  - tokens de entrada/saída por chamada
  - custo estimado (usando os preços oficiais do Gemini, mesmo o teste real
    rodando de graça no tier gratuito)
  - qualidade: se a FAQ correta (conforme gabarito) foi citada na resposta

Gera results/comparacao_rag_cag_gemini.json com todos os dados brutos, e
imprime um resumo agregado no terminal.

RESUME INCREMENTAL: cada pergunta é salva assim que termina; se a execução for
interrompida (rate limit, queda de rede), rodar de novo retoma de onde parou,
sem repetir chamadas.
"""

import json
import re
from pathlib import Path

import faq_rag
import faq_cag
import gemini_client

CAMINHO_PERGUNTAS_TESTE = Path(__file__).resolve().parent / "data" / "perguntas_teste.json"
CAMINHO_RESULTADOS = Path(__file__).resolve().parent / "results" / "comparacao_rag_cag_gemini.json"


def carregar_perguntas_teste():
    with open(CAMINHO_PERGUNTAS_TESTE, encoding="utf-8") as f:
        return json.load(f)


def extrair_faqs_citadas(texto_resposta):
    """Extrai os números de FAQ citados no texto gerado (padrão 'FAQ #N' ou 'FAQ N')."""
    return {int(n) for n in re.findall(r"FAQ\s*#?(\d+)", texto_resposta)}


def avaliar_citacao(texto_resposta, gabarito_faqs):
    """Verifica se pelo menos uma FAQ do gabarito foi citada na resposta gerada.

    Para perguntas sem gabarito (inexistente no corpus), sucesso = NENHUMA
    FAQ foi citada com confiança (resposta deveria admitir que não sabe).
    """
    citadas = extrair_faqs_citadas(texto_resposta)
    gabarito = set(gabarito_faqs)
    if not gabarito:
        return len(citadas) == 0, citadas
    return bool(citadas & gabarito), citadas


def carregar_registros_existentes():
    """Carrega registros já salvos (resume). Retorna dict {id: registro}."""
    if not CAMINHO_RESULTADOS.exists():
        return {}
    try:
        with open(CAMINHO_RESULTADOS, encoding="utf-8") as f:
            dados = json.load(f)
        return {r["id"]: r for r in dados.get("registros", [])}
    except (json.JSONDecodeError, KeyError):
        return {}


def salvar_incremental(registros_por_id):
    """Salva o estado atual em disco após cada pergunta (checkpoint de resume)."""
    registros = [registros_por_id[i] for i in sorted(registros_por_id)]
    CAMINHO_RESULTADOS.parent.mkdir(exist_ok=True)
    payload = {"resumo": montar_resumo(registros), "registros": registros}
    with open(CAMINHO_RESULTADOS, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def rodar_comparacao():
    perguntas_teste = carregar_perguntas_teste()
    faqs = faq_rag.carregar_faqs(faq_rag.CAMINHO_FAQS)

    print("Carregando modelo de embeddings e indexando FAQs (para o modo RAG)...")
    indice = faq_rag.IndiceRAG(faqs)

    print("Conectando ao Gemini...")
    client = gemini_client.obter_client()

    registros_por_id = carregar_registros_existentes()
    if registros_por_id:
        print(f"Resume: {len(registros_por_id)} pergunta(s) já feita(s), retomando as restantes.")

    for caso in perguntas_teste:
        if caso["id"] in registros_por_id:
            print(f"\n=== Pergunta #{caso['id']}: (já feita, pulando)")
            continue

        print(f"\n=== Pergunta #{caso['id']}: {caso['pergunta']}")

        print("  Rodando RAG...")
        saida_rag = faq_rag.gerar_resposta_rag(client, indice, caso["pergunta"])
        acertou_rag, citadas_rag = avaliar_citacao(saida_rag["texto"], caso["gabarito_faqs"])

        print("  Rodando CAG...")
        saida_cag = faq_cag.gerar_resposta_cag(client, faqs, caso["pergunta"])
        acertou_cag, citadas_cag = avaliar_citacao(saida_cag["texto"], caso["gabarito_faqs"])

        registro = {
            "id": caso["id"],
            "pergunta": caso["pergunta"],
            "tipo": caso["tipo"],
            "gabarito_faqs": caso["gabarito_faqs"],
            "rag": {
                "resposta": saida_rag["texto"],
                "faqs_citadas": sorted(citadas_rag),
                "acertou": acertou_rag,
                "tokens_entrada": saida_rag["tokens_entrada"],
                "tokens_saida": saida_rag["tokens_saida"],
                "latencia_s": saida_rag["latencia_s"],
                "custo_estimado_usd": saida_rag["custo_estimado_usd"],
                "top_k_recuperado": saida_rag["top_k_recuperado"],
            },
            "cag": {
                "resposta": saida_cag["texto"],
                "faqs_citadas": sorted(citadas_cag),
                "acertou": acertou_cag,
                "tokens_entrada": saida_cag["tokens_entrada"],
                "tokens_saida": saida_cag["tokens_saida"],
                "latencia_s": saida_cag["latencia_s"],
                "custo_estimado_usd": saida_cag["custo_estimado_usd"],
            },
        }
        registros_por_id[caso["id"]] = registro
        salvar_incremental(registros_por_id)  # checkpoint após cada pergunta

        print(f"  RAG: {'OK' if acertou_rag else 'ERRO'} | "
              f"{saida_rag['latencia_s']}s | "
              f"in={saida_rag['tokens_entrada']} out={saida_rag['tokens_saida']}")
        print(f"  CAG: {'OK' if acertou_cag else 'ERRO'} | "
              f"{saida_cag['latencia_s']}s | "
              f"in={saida_cag['tokens_entrada']} out={saida_cag['tokens_saida']}")

    return [registros_por_id[i] for i in sorted(registros_por_id)]


def montar_resumo(registros):
    n = len(registros)

    def media(valores):
        valores = [v for v in valores if v is not None]
        return round(sum(valores) / len(valores), 4) if valores else None

    def soma(valores):
        valores = [v for v in valores if v is not None]
        return round(sum(valores), 6) if valores else None

    acertos_rag = sum(1 for r in registros if r["rag"]["acertou"])
    acertos_cag = sum(1 for r in registros if r["cag"]["acertou"])

    return {
        "total_perguntas": n,
        "rag": {
            "acertos": acertos_rag,
            "taxa_acerto": round(acertos_rag / n, 2),
            "latencia_media_s": media([r["rag"]["latencia_s"] for r in registros]),
            "tokens_entrada_medio": media([r["rag"]["tokens_entrada"] for r in registros]),
            "tokens_saida_medio": media([r["rag"]["tokens_saida"] for r in registros]),
            "custo_total_estimado_usd": soma([r["rag"]["custo_estimado_usd"] for r in registros]),
        },
        "cag": {
            "acertos": acertos_cag,
            "taxa_acerto": round(acertos_cag / n, 2),
            "latencia_media_s": media([r["cag"]["latencia_s"] for r in registros]),
            "tokens_entrada_medio": media([r["cag"]["tokens_entrada"] for r in registros]),
            "tokens_saida_medio": media([r["cag"]["tokens_saida"] for r in registros]),
            "custo_total_estimado_usd": soma([r["cag"]["custo_estimado_usd"] for r in registros]),
        },
    }


def main():
    registros = rodar_comparacao()
    resumo = montar_resumo(registros)

    # Resumo final é regravado com o estado completo (o salvamento incremental
    # já deixou o arquivo atualizado a cada pergunta; isto só garante o resumo
    # final consistente).
    CAMINHO_RESULTADOS.parent.mkdir(exist_ok=True)
    with open(CAMINHO_RESULTADOS, "w", encoding="utf-8") as f:
        json.dump({"resumo": resumo, "registros": registros}, f, ensure_ascii=False, indent=2)

    print("\n\n========== RESUMO ==========")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(f"\nResultados completos salvos em: {CAMINHO_RESULTADOS}")


if __name__ == "__main__":
    main()
