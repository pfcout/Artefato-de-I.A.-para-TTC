# ==============================================================
#  🤖 postprocess_diarization_llm.py
#  Projeto: Tele_IA Transcrição - Pós-processamento LLM (TPST)
#  Atualização:
#   - Nova função construir_prompt com análise contextual Orto Mundi
#   - Saída alterada para a pasta 'arquivos_postprocess'
# ==============================================================

import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from jiwer import wer  # Para cálculo de cpWER/WDER aproximados


# ==============================================================
# ⚙️ Funções auxiliares
# ==============================================================

def ler_json(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def calcular_cpwer(original, revisado):
    texto_original = " ".join([seg["text"] for seg in original])
    texto_revisado = " ".join([seg["text"] for seg in revisado])
    return round(wer(texto_original, texto_revisado), 3)


def calcular_wder(original, revisado):
    total = len(original)
    erros = sum(
        1
        for i in range(min(len(original), len(revisado)))
        if original[i].get("speaker") != revisado[i].get("speaker")
    )
    return round(erros / total if total > 0 else 0.0, 3)


def executar_ollama(prompt, model="gemma2:2b"):
    """Executa o modelo local via Ollama."""
    try:
        comando = ["ollama", "run", model]
        processo = subprocess.Popen(
            comando,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        saida, _ = processo.communicate(input=prompt, timeout=300)
        return saida.strip()
    except Exception as e:
        print(f"⚠️ Erro ao chamar Ollama: {e}")
        return None


# ==============================================================
# 🔍 Prompt Template (nova versão inteligente Orto Mundi)
# ==============================================================

def construir_prompt(bloco_texto):
    return f"""
Você é um assistente especialista em analisar e corrigir transcrições de chamadas de telemarketing para a "Orto Mundi", uma empresa de materiais ortodônticos. Sua tarefa é revisar o diálogo e corrigir os rótulos [VENDEDOR] e [CLIENTE] com a máxima precisão.

---
**Lógica de Decisão (Siga esta ordem):**

1.  **Encontre o Vendedor:** A pista mais confiável é a menção à empresa. Procure por frases como "da Orto Mundi". A pessoa que diz isso é **sempre** o [VENDEDOR].
2.  **Identifique a Abertura do Vendedor:** O vendedor pode se apresentar de duas formas:
    * **Direta:** "Aqui é [Nome] da Orto Mundi."
    * **Em Etapas:** Ele primeiro pergunta pelo decisor ("Gostaria de falar com o responsável pelas compras?") e só depois de ser questionado ("De onde é?") ele revela a empresa.
3.  **Identifique o Cliente:** A(s) outra(s) pessoa(s) na chamada são o [CLIENTE]. O cliente geralmente atende a ligação ("Alô?", "Odonto Company, boa tarde.") e faz perguntas para identificar o chamador.

---
**Pistas Detalhadas:**

**1. O [VENDEDOR] (Agente da Orto Mundi):**
* **Frase-Chave:** Menciona **"da Orto Mundi"**. Esta é a regra de ouro.
* **Objetivo Claro:** Pergunta pelo "responsável pelas compras", por um "doutor(a)" específico, ou fala sobre "material de ortodontia".
* **Contexto:** Pode mencionar que a ligação é um "retorno".

**2. O [CLIENTE] (Clínica ou Doutor):**
* **Primeira Fala:** Quase sempre atende a ligação.
* **Papel de Filtro:** Frequentemente é uma recepcionista que pergunta "Quem gostaria?" ou "De onde é?" antes de transferir.
* **Contexto Interno:** Responde com informações da clínica, como "O doutor não se encontra".

**3. Cenários Comuns:**
* **O CLIENTE FALA PRIMEIRO.** Esta é a norma.
* **ATENDIMENTO AUTOMÁTICO (URA):** Qualquer saudação ou menu de robô inicial pertence ao lado do [CLIENTE].

**REGRAS DE FORMATAÇÃO:**
- Corrija APENAS os rótulos.
- NÃO altere o texto original.
- Mantenha o formato linha por linha.
---

**Transcrição para revisar:**
{bloco_texto}

**Sua Resposta (apenas a transcrição corrigida):**
"""


# ==============================================================
# 🚀 Pós-processamento principal
# ==============================================================

def main():
    import re
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir",
        default="C:/Users/Pichau/Desktop/Projeto Tele_IA Transcricao/arquivos_transcritos/json")
    parser.add_argument("--output_dir",
        default="C:/Users/Pichau/Desktop/Projeto Tele_IA Transcricao/arquivos_postprocess")
    parser.add_argument("--model", default="gemma2:2b")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "metricas_tpst.log"
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n=== Execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    for arquivo in input_dir.glob("*.json"):
        print(f"\n▶ Processando {arquivo.name}")
        dados = ler_json(arquivo)
        texto_original = [
            f"[{seg.get('speaker', 'UNK')}] {seg['text']}" for seg in dados
        ]
        prompt = construir_prompt("\n".join(texto_original))
        resposta = executar_ollama(prompt, args.model)

        if not resposta:
            print("⚠️ Falha na resposta do LLM, mantendo versão original.")
            salvar_json(dados, output_dir / arquivo.name)
            continue

        # Converter resposta em estrutura JSON revisada
        linhas = resposta.split("\n")
        revisado = []
        for linha in linhas:
            if not linha.strip():
                continue
            match = re.match(r"\[(VENDEDOR|CLIENTE)\]\s*(.+)", linha.strip(), re.IGNORECASE)
            if match:
                speaker, texto = match.groups()
                revisado.append({"speaker": speaker.upper(), "text": texto.strip()})
            else:
                revisado.append({"speaker": "UNK", "text": linha.strip()})

        # Calcular métricas antes/depois
        wder_antes = calcular_wder(dados, dados)
        wder_depois = calcular_wder(dados, revisado)
        cpwer_antes = calcular_cpwer(dados, dados)
        cpwer_depois = calcular_cpwer(dados, revisado)

        # Salvar refinado
        nome_saida = arquivo.stem + "_refinado.json"
        salvar_json(revisado, output_dir / nome_saida)

        resumo = (
            f"{arquivo.name}\n"
            f"WDER: {wder_antes} → {wder_depois}\n"
            f"cpWER: {cpwer_antes} → {cpwer_depois}\n"
            f"Correções aplicadas: {sum(1 for a, b in zip(dados, revisado) if a.get('speaker') != b.get('speaker'))}\n"
        )
        print(resumo)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(resumo + "\n")

    print("\n✅ Pós-processamento concluído. Resultados salvos em:")
    print(f"📂 {output_dir}\n📄 Log: {log_path}")


if __name__ == "__main__":
    main()