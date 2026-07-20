"""Cliente compartilhado do Gemini para geração de respostas (RAG e CAG).

Usado tanto pelo modo RAG (contexto = top-k recuperado) quanto pelo modo CAG
(contexto = todas as FAQs pré-carregadas). Centraliza a chamada à API para
que latência e contagem de tokens sejam medidas de forma consistente nos
dois modos — condição necessária para uma comparação justa.

NOTA SOBRE CACHING: o caching explícito do Gemini (economia de ~90% em
tokens repetidos) exige billing ativado; no tier gratuito usado aqui, a
tentativa de criar cache retornou cota zero (erro 429, RESOURCE_EXHAUSTED).
Por isso, todas as chamadas abaixo são feitas SEM caching — cada chamada
paga o preço cheio de entrada. Isso é uma decisão documentada, não um
descuido: ver relatorio_checkpoint_b.md para a análise dessa limitação.
"""

import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

MODELO = "gemini-3-flash-preview"

# Preços oficiais publicados (ai.google.dev/gemini-api/docs/pricing), usados
# apenas para estimar custo hipotético em tier pago — o teste real roda no
# tier gratuito e não gera cobrança.
PRECO_ENTRADA_POR_MILHAO = 0.50  # USD
PRECO_SAIDA_POR_MILHAO = 3.00    # USD

MAX_TENTATIVAS = 4
ESPERA_INICIAL_S = 5  # dobra a cada nova tentativa (backoff exponencial)


def obter_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente GEMINI_API_KEY antes de rodar.")
    return genai.Client(api_key=api_key)


def _cota_diaria_esgotada(mensagem_erro):
    """True se um 429 RESOURCE_EXHAUSTED for de cota DIÁRIA (não por minuto).

    O corpo do erro do Gemini traz o quotaId da violação: o do limite diário
    contém 'PerDay' (ex.: GenerateRequestsPerDayPerProjectPerModel-FreeTier),
    enquanto o de limite por minuto contém 'PerMinute'. Checar 'PerDay'
    distingue os dois de forma inequívoca (o 'per day' cobre o texto humano).
    """
    m = mensagem_erro.lower()
    return "perday" in m or "per day" in m


def gerar_resposta(client, system_instruction, conteudo_usuario):
    """Chama o Gemini e retorna texto, tokens de entrada/saída e latência.

    Sem caching (ver nota no topo do arquivo). Cada chamada é uma requisição
    completa e independente.

    Inclui retry com backoff para erros transitórios: 503 "high demand" e
    429 "resource exhausted" por limite POR MINUTO (RPM) — comuns no modelo
    preview usado aqui, de capacidade mais restrita que modelos estáveis.

    IMPORTANTE: um 429 de cota DIÁRIA (limite de requests/dia do free tier) NÃO
    é re-tentado — re-tentar não ajuda (a cota só zera no reset do dia) e cada
    tentativa ainda consome uma request do limite, acelerando o esgotamento.
    Nesse caso a chamada aborta de imediato com mensagem clara.
    """
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            inicio = time.perf_counter()
            resposta = client.models.generate_content(
                model=MODELO,
                contents=conteudo_usuario,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
            fim = time.perf_counter()
            break
        except genai_errors.ServerError as e:
            if tentativa == MAX_TENTATIVAS:
                raise
            espera = ESPERA_INICIAL_S * (2 ** (tentativa - 1))
            print(f"    [aviso] servidor ocupado (tentativa {tentativa}/{MAX_TENTATIVAS}), "
                  f"aguardando {espera}s antes de tentar de novo...")
            time.sleep(espera)
        except genai_errors.ClientError as e:
            mensagem = str(e)
            if "RESOURCE_EXHAUSTED" not in mensagem:
                raise  # 4xx não relacionado a cota (ex.: chave inválida) — não re-tenta
            if _cota_diaria_esgotada(mensagem):
                # Cota DIÁRIA esgotada: re-tentar é inútil (só zera no reset do
                # dia) e ainda gastaria uma request do limite a cada tentativa.
                print("    [erro] cota DIÁRIA do free tier esgotada — re-tentar não "
                      "ajuda (só zera no reset diário). Abortando esta chamada.")
                raise
            if tentativa < MAX_TENTATIVAS:
                # Limite POR MINUTO: transitório, vale re-tentar com backoff.
                espera = ESPERA_INICIAL_S * (2 ** (tentativa - 1))
                print(f"    [aviso] limite de requisições por minuto atingido, "
                      f"aguardando {espera}s...")
                time.sleep(espera)
            else:
                raise

    uso = resposta.usage_metadata
    tokens_entrada = uso.prompt_token_count if uso else None
    tokens_saida = uso.candidates_token_count if uso else None

    return {
        "texto": resposta.text,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "latencia_s": round(fim - inicio, 3),
        "custo_estimado_usd": estimar_custo(tokens_entrada, tokens_saida),
    }


def estimar_custo(tokens_entrada, tokens_saida):
    """Custo hipotético em tier pago, usando os preços oficiais do Gemini 2.5 Flash."""
    if tokens_entrada is None or tokens_saida is None:
        return None
    custo = (tokens_entrada / 1_000_000) * PRECO_ENTRADA_POR_MILHAO
    custo += (tokens_saida / 1_000_000) * PRECO_SAIDA_POR_MILHAO
    return round(custo, 6)