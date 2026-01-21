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

Nesse modelo, o vendedor atua como **consultor**, guiando a conversa de forma analítica e orientada à decisão.

O método **SPIN Selling** é amplamente utilizado como base conceitual para TTC, pois estrutura o diálogo em **Situação, Problema, Implicação e Necessidade-Benefício**.

Este projeto utiliza IA para **avaliar objetivamente a qualidade dessas interações**, algo que tradicionalmente depende apenas de análise humana.

---

## Objetivos do projeto

O projeto foi desenvolvido com foco em:

- clareza metodológica  
- reprodutibilidade acadêmica  
- aplicação profissional em ambientes de TTC  
- segurança de dados (não persistência de áudios e transcrições)  

---

## Visão geral do funcionamento

O **SPIN Analyzer** permite avaliar ligações a partir de:

- Transcrições em texto (formato `[VENDEDOR]` / `[CLIENTE]`)
- Áudios WAV (transcrição automática com fallback seguro)

Fluxo geral:

1. Transcrição do áudio (quando aplicável)  
2. Análise SPIN via motor Zero-Shot  
3. Avaliação estruturada (pontuação por critério)  
4. Consolidação em painel interativo (Streamlit)  

O painel **não armazena permanentemente** arquivos enviados (WAV ou TXT).  
Todos os dados de entrada são tratados como temporários.

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
├─ scripts_auxiliar/          # Scripts de apoio
│
├─ requirements/              # Requisitos separados por ambiente
│   ├─ requirements_transcricao.txt
│   ├─ requirements_zero_shot.txt
│   └─ requirements_painel.txt
│
├─ arquivos_transcritos/      # (não versionado) entradas temporárias
├─ saida_excel/               # (não versionado) resultados
├─ saida_avaliacao/           # (não versionado) avaliações
│
├
├─ .gitignore
└─ README.md
````

> Pastas de dados, uploads, backups e resultados **não são versionadas**, por segurança e boas práticas.

---

## Requisitos

* Python **3.11 recomendado** (compatível com 3.10)
* **Evite Python 3.13** (pode causar incompatibilidades com áudio/ASR)
* Windows (ambiente principal testado)
* CPU (GPU é opcional)
* Configuração local do **Ollama** para inferência LLM

---

## Instalação — do zero (Windows)

## 3 ambientes virtuais 

### 1. Clonar o repositório

```bash
git clone https://github.com/pfcout/Artefato-de-I.A.-para-TTC.git
cd Artefato-de-I.A.-para-TTC
```

---

### 2. Ambiente de TRANSCRIÇÃO (script 01)

```powershell
py -3.11 -m venv .venv_transcricao
.\.venv_transcricao\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_transcricao.txt
```

Executar:

```powershell
python .\scripts_base\01_transcricao.py
```

---

### 3. Ambiente ZERO-SHOT (script 02)

```powershell
py -3.11 -m venv .venv_zeroshot
.\.venv_zeroshot\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_zero_shot.txt
```

Executar:

```powershell
python .\scripts_base\02_zeroshot.py
```

---

### 4. Ambiente do PAINEL (script 04)

```powershell
py -3.11 -m venv .venv_painel
.\.venv_painel\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_painel.txt
```

Executar:

```powershell
streamlit run .\scripts_base\04_painel.py
```

---

## Configuração do Ollama (LLM local)

Certifique-se de que o Ollama esteja instalado e em execução:

```bash
ollama serve
```

Exemplo de modelo:

```bash
ollama pull llama3
```

Os scripts utilizam comunicação HTTP local com o Ollama.

---

## Execução avançada (sem painel)

Os scripts em `scripts_base/` podem ser executados de forma modular para:

* reprodutibilidade acadêmica
* auditoria metodológica
* experimentos controlados

Scripts principais:

* `01_transcricao.py` — transcrição e diarização
* `02_zeroshot.py` — análise semântica
* `03_avaliacao_zeroshot.py` — avaliação estruturada
* `04_painel.py` — orquestrador Streamlit

> Para a maioria dos usuários, recomenda-se **utilizar apenas o painel**.

---

## Segurança e privacidade

* Arquivos WAV são apagados automaticamente
* Transcrições são temporárias
* Nenhum áudio é persistido
* Apenas métricas agregadas podem ser salvas (opcional)

Projeto desenvolvido para **uso acadêmico e profissional responsável**.

---

## Créditos e autoria

### Inspiração técnica

Projeto inspirado no motor Zero-Shot de:

**Lucas Schwarz**
[https://github.com/TheLucasSchwarz/zeroshotENGINE](https://github.com/TheLucasSchwarz/zeroshotENGINE)

---

### Autoria

* **Criador:** Paulo Coutinho
* **Colaborador:** Lucas Gabriel Ferreira Gomes
  *(Freelancer / Cientista de Dados)*

---

## Licença

Distribuído sob a **Apache License 2.0**.

* Uso, modificação e redistribuição permitidos
* Créditos devem ser mantidos
* Software fornecido “como está”, sem garantias

Consulte o arquivo `LICENSE`.

---

## Observações finais

Este repositório foi estruturado para:

* uso acadêmico (TCC, TTC, pesquisa aplicada)
* avaliação técnica de interações consultivas
* boas práticas de engenharia de software
* compatibilidade com GitHub e Streamlit Cloud

Sugestões e melhorias podem ser discutidas via **Issues**.
