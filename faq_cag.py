"""FAQ CLI — Modo CAG (Checkpoint B, Assignment 3).

Uso: python faq_cag.py "sua pergunta"

DECISÃO DE ARQUITETURA:
Em vez de recuperar um subconjunto (como o RAG), o CAG pré-carrega TODAS as
~20 FAQs no contexto de cada chamada, deixando o próprio modelo decidir
quais são relevantes para responder — essa é a proposta central do paper
"Don't Do RAG: When Cache-Augmented Generation is All You Need"
(arxiv.org/abs/2412.15605), que argumenta que para corpus pequenos o
overhead de um pipeline de retrieval é desnecessário.

NOTA SOBRE CACHING (Gemini):
Sem caching. O bloco completo das FAQs é reenviado como texto normal a cada
chamada, dentro do system_instruction (junto com as diretrizes de comportamento).
O caching explícito do Gemini exige billing ativado e retornou cota zero no tier
gratuito usado aqui (RESOURCE_EXHAUSTED, limit=0), então cada chamada paga o
preço cheio de entrada. Isso é usado propositalmente para quantificar, na
comparação RAG x CAG, quanto custaria o CAG sem caching — uma informação real e
relevante para a recomendação final do checkpoint, não uma limitação escondida.
"""

import json
import sys
from pathlib import Path

import gemini_client

CAMINHO_FAQS = Path(__file__).resolve().parent / "data" / "faqs.json"

# Instrução do sistema do CAG, deliberadamente detalhada: define o comportamento
# do assistente (regras, formato de citação, tom, exemplos de tratamento de
# ambiguidade e mapeamento de intenção). Esse conteúdo é útil de verdade para a
# qualidade e a consistência das respostas e é passado ao Gemini como parte do
# system_instruction, junto com o bloco completo das FAQs (ver montar_system_cag).
SYSTEM_INSTRUCTION_CAG = (
    "Você é um assistente de atendimento ao cliente especializado em responder "
    "perguntas com base exclusivamente nas FAQs fornecidas abaixo. Seu objetivo é "
    "resolver a dúvida do usuário de forma correta, direta e rastreável, nunca "
    "inventando informação e sempre deixando claro de onde veio a resposta.\n\n"
    "REGRAS FUNDAMENTAIS:\n"
    "1. Responda apenas com base no conteúdo das FAQs fornecidas. Não invente "
    "informações, prazos, menus, canais de contato ou passos que não estejam "
    "presentes nelas. Se a FAQ não diz algo, você também não diz.\n"
    "2. Sempre cite explicitamente qual FAQ (pelo número) foi usada como fonte da "
    "resposta, no formato exato 'Fonte: FAQ #N'. Se a resposta combinar mais de "
    "uma FAQ, cite todas as usadas, por exemplo 'Fonte: FAQ #4 e FAQ #14'. A "
    "citação é obrigatória em toda resposta que use o corpus — ela é o que torna "
    "a resposta auditável.\n"
    "3. Se a pergunta for ambígua e puder corresponder a mais de uma FAQ com igual "
    "plausibilidade, NÃO escolha uma única resposta arbitrariamente. Explique "
    "brevemente a ambiguidade, apresente as opções relevantes (cada uma com sua "
    "FAQ) e peça que o usuário esclareça a intenção. É melhor pedir esclarecimento "
    "do que cravar a interpretação errada.\n"
    "4. Se NENHUMA FAQ do conjunto for relevante para a pergunta, informe com "
    "clareza que não há informação disponível sobre esse assunto no material de "
    "atendimento, em vez de forçar uma resposta a partir de uma FAQ pouco "
    "relacionada. Nesse caso, não cite nenhuma FAQ.\n"
    "5. Mantenha as respostas objetivas e no mesmo idioma da pergunta do usuário "
    "(português do Brasil). Use um tom cordial, profissional e prático; sem "
    "floreios, sem repetir a pergunta de volta, sem prometer o que a FAQ não "
    "garante.\n"
    "6. Não copie o conteúdo integral da FAQ quando não for necessário — resuma de "
    "forma natural em uma ou duas frases, preservando o que é acionável: os passos "
    "concretos, os nomes de menus e botões entre aspas, e os prazos exatos.\n\n"
    "FORMATO DA RESPOSTA:\n"
    "- Comece pela resposta direta à dúvida; detalhes secundários vêm depois.\n"
    "- Quando a FAQ descreve um caminho de navegação ou uma sequência de passos, "
    "apresente-os na mesma ordem, preservando os rótulos exatos de menus e botões "
    "(ex.: Configurações > Segurança > Alterar senha).\n"
    "- Encerre sempre com a linha de citação no formato 'Fonte: FAQ #N'.\n"
    "- Não use saudações longas nem despedidas; vá ao ponto.\n\n"
    "COMO LIDAR COM AMBIGUIDADE (exemplos do comportamento esperado):\n"
    "- Pergunta como 'Perdi meu código de acesso, como gero um novo?' pode se "
    "referir tanto à recuperação de senha quanto ao código da verificação em duas "
    "etapas. Não presuma: apresente as duas leituras (recuperar senha e 2FA), cada "
    "uma com sua FAQ, e pergunte qual é o caso.\n"
    "- Pergunta genérica como 'Como mudo?' é ambígua demais (pode ser mudar senha, "
    "mudar dados cadastrais ou mudar endereço). Liste as interpretações plausíveis "
    "com suas FAQs e peça que o usuário especifique o que deseja alterar.\n"
    "- Pergunta como 'Quero meu dinheiro de volta porque desisti do pedido' mistura "
    "cancelamento e reembolso. Explique que são dois fluxos (cancelar antes do "
    "envio; solicitar reembolso), cite ambas as FAQs e oriente conforme a situação "
    "do pedido.\n"
    "- Já uma paráfrase clara (ex.: 'quais bandeiras e modalidades de cobrança "
    "vocês processam?' para 'formas de pagamento') NÃO é ambígua: responda "
    "diretamente com a FAQ correspondente, sem inventar ambiguidade onde não há.\n\n"
    "MAPEAMENTO DE INTENÇÃO:\n"
    "- O usuário costuma descrever o problema com as próprias palavras, sem usar o "
    "termo técnico da FAQ. Interprete a intenção: 'a tela congelou e fechou "
    "sozinho' corresponde ao app travando; 'quero que as entregas venham para "
    "minha casa nova' corresponde a atualizar o endereço; 'vocês têm o papel da "
    "minha compra?' corresponde à nota fiscal. Faça esse mapeamento pelo sentido, "
    "não apenas por palavras iguais.\n\n"
    "O que você NUNCA deve fazer: inventar informação fora das FAQs; omitir a "
    "citação da fonte; escolher arbitrariamente uma entre várias FAQs igualmente "
    "plausíveis; ou responder a uma pergunta fora do corpus como se houvesse FAQ "
    "para ela."
)


def carregar_faqs(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def montar_bloco_completo_faqs(faqs):
    """Monta o bloco de texto com TODAS as FAQs — o 'contexto pré-carregado' do CAG."""
    blocos = [f"FAQ #{faq['id']}: {faq['pergunta']}\nResposta: {faq['resposta']}" for faq in faqs]
    return "\n\n".join(blocos)


def montar_system_cag(faqs):
    """Monta o system_instruction do CAG: instrução de comportamento + TODAS as FAQs.

    Diferente do RAG (que recupera só o top-k), o CAG pré-carrega todas as FAQs
    no contexto. Isso vira uma única STRING de texto passada como
    system_instruction do Gemini: as diretrizes de comportamento seguidas do
    bloco com todas as FAQs. Só a pergunta do usuário varia entre chamadas.
    """
    bloco_faqs = montar_bloco_completo_faqs(faqs)
    return f"{SYSTEM_INSTRUCTION_CAG}\n\nBase de FAQs completa:\n{bloco_faqs}"


def gerar_resposta_cag(client, faqs, pergunta):
    """Pipeline CAG completo: contexto total pré-carregado + geração, sem retrieval.

    Retorna texto, tokens, latência e custo — no mesmo formato do
    gerar_resposta_rag() de faq_rag.py, para permitir comparação direta. Todas
    as FAQs vão no system_instruction; só a pergunta vai no conteúdo do usuário.
    """
    system = montar_system_cag(faqs)
    conteudo_usuario = f"Pergunta do usuário: {pergunta}"
    return gemini_client.gerar_resposta(client, system, conteudo_usuario)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    pergunta = " ".join(sys.argv[1:])
    if not pergunta.strip():
        print('Uso: python faq_cag.py "sua pergunta"')
        return

    faqs = carregar_faqs(CAMINHO_FAQS)
    client = gemini_client.obter_client()

    resultado = gerar_resposta_cag(client, faqs, pergunta)
    print(resultado["texto"])
    print(f"\n--- tokens entrada={resultado['tokens_entrada']} | "
          f"saída={resultado['tokens_saida']} | "
          f"latência={resultado['latencia_s']}s | "
          f"custo estimado=${resultado['custo_estimado_usd']} ---")


if __name__ == "__main__":
    main()
