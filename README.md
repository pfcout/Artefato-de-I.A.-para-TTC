<<<<<<< HEAD
# 📚 Projeto Tele_IA — README Consolidado (Transcrição • Zero‑Shot SPIN • Avaliação • Painel)

**Autor:** Paulo Coutinho  
**Versão:** 2025.10  
**SO alvo:** Windows 10/11  
**Execução local:** 100% offline (Ollama + Python)  
**Repos/estruturas integradas:** Transcrição (WhisperX), SPIN Zero‑Shot, Avaliação Avançada, Painel Streamlit

---

## 1) Objetivo e Escopo

Este documento consolida, de forma acadêmica e reprodutível, a arquitetura, o fluxo operacional e o plano de **validação** do ecossistema Tele_IA:  
1) **Transcrição + Diarização** (WhisperX + Pyannote);  
2) **Classificação Zero‑Shot** das fases **SPIN Selling** com camadas de **Behavior Analysis**;  
3) **Avaliação Avançada** (pontuação final e feedbacks);  
4) **Painel Interativo** (Streamlit) para visualização e análise.

---

## 2) Arquitetura Lógica do Sistema

```
Áudio (.wav) ─▶ [01_transcricao.py]
                ├─ Transcreve (WhisperX)
                ├─ Diariza (Pyannote 3.1 via WhisperX)
                └─ Normaliza/corrige (dicionário + pontuação)

TXT/JSON ─▶ [02_zeroshot.py]
             ├─ Modelo local (gemma2:2b via Ollama)
             ├─ Prompts estruturados (prompt_structure_SPIN.xlsx)
             ├─ Dupla validação (double_shot)
             └─ Consolida Excel bruto (resultados_completos_SPIN.xlsx)

Excel bruto ─▶ [03_avaliacao_zeroshot.py]
               ├─ Cálculo de pontuação/nota 0–10
               ├─ Consistência/Conflito
               └─ Gera avaliação final (avaliacao_spin_avancada.xlsx + resumo TXT)

Excel final ─▶ [04_painel.py] (Streamlit)
               └─ Visualização por vendedor/ligação + feedbacks
```

**Referências internas:** Estruturas e fluxos acima são extraídos dos READMEs do Painel e do Zero‑Shot (ver Seção 8, Referências Internas).

---

## 3) Estrutura de Pastas (Consolidada)

```
Projeto Tele_IA Transcricao/
│
├─ .venv_transcricao/      # WhisperX + Pyannote (transcrição/diarização)
├─ .venv_zeroshot/         # Ollama + ZeroShotENGINE (classificação SPIN)
├─ .venv_painel/           # Streamlit + libs de visualização
├─ .venv_metricas/         # (opcional) Métricas de diarização
│
├─ bd_ligacoes_filtradas/  # áudios .wav de entrada
├─ arquivos_transcritos/
│   ├─ txt/                # saídas TXT da transcrição (entrada do Zero‑Shot)
│   └─ json/               # metadados estruturados
│
├─ perguntas_spin/
│   └─ prompt_structure_SPIN.xlsx   # blocos de prompt SPIN/BA
│
├─ saidas_txt/             # relatórios textuais do Zero‑Shot por arquivo
├─ saida_excel/
│   └─ resultados_completos_SPIN.xlsx
│
├─ saida_avaliacao/
│   ├─ excel/
│   │   └─ avaliacao_spin_avancada.xlsx
│   └─ txt/
│       └─ resumo_avaliacao_SPIN.txt
│
└─ scripts/
    ├─ 01_transcricao.py
    ├─ 02_zeroshot.py
    ├─ 03_avaliacao_zeroshot.py
    └─ 04_painel.py
=======
# Artefato de I.A. para TTC  

Este repositório apresenta um **artefato de Inteligência Artificial aplicado a TTC (Televendas Técnico-Consultivas)**, materializado em um painel acadêmico e técnico para análise automática de ligações de vendas utilizando o método **SPIN Selling**.

O sistema combina **transcrição de áudio**, **análise semântica via LLM (Zero-Shot)** e **avaliação estruturada por critérios**, com foco em reprodutibilidade, clareza metodológica e uso responsável.

---

## O que é TTC — Televendas Técnico-Consultivas

**TTC (Televendas Técnico-Consultivas)** é um modelo de vendas no qual o contato telefônico vai além da abordagem comercial tradicional, priorizando:

- diagnóstico estruturado do contexto do cliente  
- entendimento técnico do problema ou necessidade  
- exploração de impactos e implicações  
- construção de valor antes da oferta de solução  

Nesse modelo, o vendedor atua como **consultor**, guiando a conversa de forma analítica e orientada a decisão.  
O método **SPIN Selling** é amplamente utilizado como base conceitual para TTC, pois estrutura o diálogo em **Situação, Problema, Implicação e Necessidade-Benefício**.

Este projeto utiliza IA para **avaliar objetivamente a qualidade dessas interações**, algo que normalmente depende apenas de análise humana.

---

## Objetivos do projeto

O projeto foi desenvolvido com foco em:

- clareza metodológica  
- reprodutibilidade acadêmica  
- aplicação profissional em ambientes de TTC  
- segurança de dados (não persistência de áudios e transcrições)  

---

## Visão geral do funcionamento

O SPIN Analyzer permite avaliar ligações a partir de:

- Transcrições em texto (formato `[VENDEDOR]` / `[CLIENTE]`)
- Áudios WAV (transcrição automática com fallback seguro)

Fluxo geral:

1. Transcrição do áudio (quando aplicável)  
2. Análise SPIN via motor Zero-Shot  
3. Avaliação estruturada (pontuação por critério)  
4. Consolidação em painel interativo (Streamlit)  

O painel **não armazena permanentemente** arquivos enviados (WAV ou TXT). Todos os dados de entrada são tratados como temporários.

---

## Estrutura do projeto

```text
Projeto Tele_IA Transcricao/
│
├─ scripts_base/              # Núcleo do projeto (fluxo principal)
│   ├─ 01_transcricao.py
│   ├─ 02_zeroshot.py
│   ├─ 03_avaliacao_zeroshot.py
│   └─ 04_painel.py
│
├─ zeroshot_engine/           # Motor Zero-Shot (adaptado)
├─ scripts_auxiliar/          # Scripts de apoio (métricas, pós-processamento)
├─ tools/                     # Ferramentas internas (scan, manutenção)
│
├─ arquivos_transcritos/      # (não versionado) entradas temporárias
├─ saida_excel/               # (não versionado) resultados gerados
├─ saida_avaliacao/           # (não versionado) avaliações finais
│
├─ requirements.txt
├─ .gitignore
└─ README.md
````

> Pastas de dados, uploads, backups e resultados **não são versionadas**, por segurança e boas práticas.

---

## Requisitos

* Python **3.10 ou superior**
* Windows (ambiente principal testado)
* CPU (GPU é opcional)
* Configuração local do **Ollama** para inferência LLM

---

## Instalação — do zero

### 1. Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/artefato-ia-para-ttc.git
cd artefato-ia-para-ttc
>>>>>>> f9bcafcef7ea3e23cf99441fc09a9ca5b93ff755
```

---

<<<<<<< HEAD
## 4) Ambientes Virtuais (Isolamento por Domínio)

- **`.venv_transcricao`**: WhisperX, Pyannote 3.1, Torch, utilitários de texto.  
- **`.venv_zeroshot`**: Ollama, zeroshot-engine, pandas/numpy compatíveis à classificação.  
- **`.venv_painel`**: Streamlit, pandas/openpyxl, plotly/altair.  
- **`.venv_metricas` (opcional)**: pyannote.metrics==3.2.1, numpy==2.0.1, pandas==2.2.3 (cálculo DER/F‑measure).

Racional: evitar conflitos de versões (ex.: `numpy`/`pandas` diferentes exigidas por WhisperX e Zero‑Shot).

---

## 5) Execução — Passo a Passo (Reprodutível)

### 5.1 Transcrição + Diarização
```
.venv_transcricao\Scripts\activate
python scripts\01_transcricao.py
```
- Entrada: `bd_ligacoes_filtradas\*.wav`  
- Saída: `arquivos_transcritos\txt\*.txt` e `arquivos_transcritos\json\*.json`  
- Observações: uso de dicionário léxico + pontuação (quando disponível).

### 5.2 Classificação Zero‑Shot (SPIN + BA)
```
.venv_zeroshot\Scripts\activate
python scripts\02_zeroshot.py
```
- Lê TXT de `arquivos_transcritos\txt\`  
- Executa via **Ollama** com **gemma2:2b**, **dupla validação** e **prompts estruturados**  
- Gera: `saidas_txt\resultado_*.txt` + `saida_excel\resultados_completos_SPIN.xlsx`.

### 5.3 Avaliação Avançada
```
.venv_zeroshot\Scripts\activate
python scripts\03_avaliacao_zeroshot.py
```
- Calcula pontuação/nota final, consistência e conflitos  
- Gera: `saida_avaliacao\excel\avaliacao_spin_avancada.xlsx` + `saida_avaliacao\txt\resumo_avaliacao_SPIN.txt`.

### 5.4 Painel (Streamlit)
```
.venv_painel\Scripts\activate
streamlit run scripts\04_painel.py
```
- Lê: `saida_avaliacao\excel\avaliacao_spin_avancada.xlsx`  
- Exibe seleção **Vendedor/Ligação**, métricas e feedbacks.

> Status atual do painel: há um bug de atualização de widgets (selectbox) ainda **não resolvido**; ver Seção 8 (Referências Internas) e Apêndice A para registro do problema e próximos passos.

---

## 6) Metodologia de Classificação (Macro SPIN + Micro BA)

- **Macro (SPIN Selling)**: Abertura, Situação, Problema, Implicação, Necessidade (Need‑Payoff).  
- **Micro (Behavior Analysis)**: 13 categorias distribuídas em Iniciar, Esclarecer, Reagir, Processar (ex.: *Seeking Information*, *Summarizing*, *Proposing*, *Supporting*, etc.).  
- O classificador zero‑shot considera **intenção** e **efeito da fala**; sobreposições são aceitas (p.ex., *Summarizing* + *Testing Understanding* no mesmo trecho).  
- **Dupla validação** (`double_shot=True`): o sistema executa duas passagens e compara resultados por fase (método `identical` vs `conflict`) para estimar consistência.

---

## 7) Plano de Validação Acadêmica (Garcia et al., 2025)

**Objetivo:** avaliar **desempenho** (AUC/F1) e **estabilidade intra‑modelo** (RCR, Spearman ρ) em duas execuções independentes do `02_zeroshot.py` sobre o mesmo conjunto de textos.  
**Ambiente dedicado:** `.venv_validacao` (pandas, scikit‑learn, scipy, openpyxl).  
**Fluxo resumido:**  
1) Executar o `02_zeroshot.py` duas vezes e salvar `resultados_completos_SPIN.xlsx` e `resultados_completos_SPIN_RUN2.xlsx`;  
2) Rodar `validacao_garcia_spin.py` para consolidar métricas (gera XLSX + TXT em `saida_avaliacao`).  
3) (Opcional) Comparar com padrão‑ouro humano em `avaliacao_humana_SPIN.xlsx` (κ por fase).

**Métricas‑chave e limiares sugeridos:**  
- **AUC** ≥ 0,80 (excelente); 0,65–0,79 (boa); < 0,65 (fraca)  
- **F1** ≥ 0,75 (alto); 0,60–0,74 (moderado); < 0,60 (insuficiente)  
- **RCR** ≥ 0,80 (estabilidade intra‑modelo)  
- **Spearman ρ** ≥ 0,75 (correlação ordinal entre runs)

**Critérios de aprovação (passa/não passa):**  
- ≥ 3 de 5 fases com **AUC ≥ 0,80** e **F1 ≥ 0,75**;  
- Estabilidade global com **RCR ≥ 0,80** e **ρ ≥ 0,75** em ≥ 3 fases;  
- (Opcional) Concordância humana **κ ≥ 0,70** por fase.

---

## 8) Referências Internas (documentos do projeto)

- **Painel (Streamlit)** — Visão geral, estrutura e *bug* de atualização registrado (README do painel).  
- **Zero‑Shot SPIN** — Guia completo (arquitetura, prompts, dupla validação, saídas).  
- **Transcrição** — Pipeline v2 (WhisperX, alinhamento, diarização).  
- **Validação** — Protocolo formal baseado em Garcia et al., 2025.

---

## 9) Boas Práticas e Reprodutibilidade

- **Isolamento por venv** (transcrição / zeroshot / painel / métricas).  
- **Controle de versões** de `numpy/pandas/av/whisperx` por ambiente para evitar conflitos.  
- **Logs**: salvar prints e tempos por etapa (úteis para anexos de dissertação).  
- **Arquivamento**: manter `*.xlsx` e `*.txt` gerados, além de **hashes** e versões dos pacotes.

---

## 10) Execução Rápida (Resumo de Comandos)

```powershell
# 01) Transcrição
.venv_transcricao\Scripts\activate
python scripts\01_transcricao.py

# 02) Classificação Zero‑Shot
.venv_zeroshot\Scripts\activate
python scripts\02_zeroshot.py

# 03) Avaliação Avançada
.venv_zeroshot\Scripts\activate
python scripts\03_avaliacao_zeroshot.py

# 04) Painel (Streamlit)
.venv_painel\Scripts\activate
streamlit run scripts\04_painel.py
=======
### 2. Criar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\activate
>>>>>>> f9bcafcef7ea3e23cf99441fc09a9ca5b93ff755
```

---

<<<<<<< HEAD
## Apêndice A — Status do Painel
Há **inconsistência de atualização** ao trocar vendedor/ligação (widgets `selectbox` não forçam rerender e o DataFrame exibe a primeira linha). Tentativas (reset de `session_state`, normalização de colunas, limpeza de cache, novo venv) **não resolveram**; recomenda‑se criar reprodutor mínimo, testar `st.experimental_rerun()` e alternativas de seleção. Registro formal preservado para transparência metodológica.

---

> **Nota:** Todos os caminhos e scripts citados refletem a consolidação do projeto na pasta **Transcrição**, com numeração sequencial `01_… 04_…` para o pipeline completo.
=======
### 3. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Ambientes virtuais **não são versionados**. A reprodução do projeto é feita exclusivamente via `requirements.txt`.

---

### 4. Configurar o Ollama (LLM local)

Certifique-se de que o Ollama esteja instalado e em execução:

```bash
ollama serve
```

Exemplo de download de modelo:

```bash
ollama pull llama3
```

Os scripts utilizam comunicação HTTP local com o Ollama.

---

## Executando o painel

Na raiz do projeto, com a venv ativa:

```bash
streamlit run scripts_base/04_painel.py
```

O painel será aberto automaticamente no navegador.

---

## Painel online (Streamlit Cloud)

> Ainda não publicado

Quando disponível, o painel poderá ser acessado abaixo:

<p align="center">
  <a href="LINK_A_SER_ADICIONADO" target="_blank">
    <img src="https://img.shields.io/badge/Acessar%20Painel-Streamlit-blue?style=for-the-badge" />
  </a>
</p>

---

## Segurança e privacidade

* Arquivos WAV enviados são apagados automaticamente
* Transcrições temporárias são removidas após o processamento
* Nenhum áudio ou conversa é persistido
* Apenas métricas agregadas podem ser salvas localmente (opcional)

O projeto foi desenhado para **uso acadêmico e profissional responsável**, especialmente em contextos de TTC.

---

## Créditos e autoria

### Inspiração técnica

Este projeto foi **inspirado** no motor Zero-Shot desenvolvido por:

**Lucas Schwarz**
[https://github.com/TheLucasSchwarz/zeroshotENGINE](https://github.com/TheLucasSchwarz/zeroshotENGINE)

O projeto original serviu como base conceitual para a adaptação do motor de análise semântica.

---

### Autoria do projeto

* **Criador do projeto:**
  **Paulo Coutinho**

* **Ajudante:**
  **Lucas Gabriel Ferreira Gomes**
  *(Freelancer / Cientista de Dados)*

---

## Licença

Este projeto é distribuído sob a **Apache License 2.0**, mantendo compatibilidade com o projeto que o inspirou.

* Uso, modificação e redistribuição são permitidos
* Créditos ao projeto original devem ser mantidos
* O software é fornecido “no estado em que se encontra”, sem garantias

Recomenda-se a leitura completa do arquivo `LICENSE`.

---

## Observações finais

Este repositório foi estruturado para:

* uso acadêmico (TCC, TTC, pesquisa aplicada)
* avaliação técnica de interações consultivas
* boas práticas de engenharia de software
* compatibilidade com GitHub e Streamlit Cloud

Sugestões e melhorias podem ser discutidas via Issues.
>>>>>>> f9bcafcef7ea3e23cf99441fc09a9ca5b93ff755
