# Artefato de Inteligência Artificial para Televendas Técnico-Consultivas (TTC)

Este repositório apresenta um **artefato acadêmico de Inteligência Artificial**, desenvolvido como objeto de estudo do **Mestrado Acadêmico em Administração da Universidade Feevale**, com foco na **Inteligência Comercial aplicada a Televendas Técnico-Consultivas (TTC)**.

O artefato materializa-se em um **pipeline completo de análise automática de ligações de vendas**, integrando:

* **Transcrição automática de áudio**
* **Análise semântica via Modelos de Linguagem (LLM) em modo Zero-Shot**
* **Avaliação estruturada baseada no método SPIN Selling (Rackham, 1988)**
* **Visualização analítica por meio de painel interativo**

O projeto foi concebido para atender simultaneamente a **rigor científico**, **aplicabilidade organizacional** e **reprodutibilidade metodológica**, respeitando princípios de **segurança, ética e uso responsável de dados**.

---

## 🔎 Acesso Rápido — Painel Online (Streamlit Cloud)

Para **visualização imediata** do artefato **sem necessidade de instalação local**, utilize o painel publicado no Streamlit Cloud:

👉 **[https://artefato-de-ia-para-ttc-cqiwcwa9yam3osormngbju.streamlit.app](https://artefato-de-ia-para-ttc-cqiwcwa9yam3osormngbju.streamlit.app)**

---

## Contexto Acadêmico

Este artefato é resultado do:

**Mestrado Acadêmico em Administração — Universidade Feevale**
**Linha de Pesquisa:** Inovação para Competitividade

**Título do Trabalho:**
*Desenvolvimento de um Artefato de Inteligência Artificial para Potencializar a Inteligência Comercial em Televendas Técnico-Consultivas*

O desenvolvimento segue os princípios da **Design Science Research (DSR)**, cujo objetivo é criar um artefato útil, fundamentado teoricamente e validável em contexto organizacional real.

---

## O que é TTC — Televendas Técnico-Consultivas

**Televendas Técnico-Consultivas (TTC)** representam um modelo de vendas complexas no qual o contato telefônico vai além da abordagem comercial tradicional. O foco está em:

* diagnóstico estruturado do contexto do cliente
* compreensão técnica do problema ou necessidade
* exploração das implicações e impactos do cenário atual
* construção explícita de valor antes da proposição de solução

Nesse modelo, o vendedor atua como **consultor**, conduzindo a conversa de forma analítica e orientada à decisão.

O método **SPIN Selling**, proposto por **Neil Rackham (1988)**, estrutura esse processo em quatro fases:

* Situação
* Problema
* Implicação
* Necessidade–Benefício (Need-Payoff)

Este projeto utiliza Inteligência Artificial para **avaliar objetivamente a qualidade dessas interações**, reduzindo a dependência exclusiva de avaliações humanas subjetivas.

---

## Visão Geral do Funcionamento do Artefato

O artefato pode operar de duas formas:

### ✔️ Modo Simplificado (Recomendado para Iniciantes)

* Uso direto do **painel Streamlit**
* Ideal para análise de resultados já processados

### ✔️ Modo Completo (Execução Manual do Pipeline)

* Execução sequencial dos scripts:

  1. Transcrição de áudio
  2. Análise SPIN via LLM (Zero-Shot)
  3. Avaliação estruturada
  4. Visualização no painel

---

## Arquitetura do Artefato

O sistema foi construído sobre três pilares fundamentais:

1. **Transcrição de Áudio**
   Conversão de chamadas telefônicas (WAV) em texto estruturado.

2. **Análise Semântica via LLM (Zero-Shot)**
   Classificação automática das falas segundo as fases do SPIN Selling, sem treinamento supervisionado.

3. **Avaliação Estruturada**
   Geração de indicadores objetivos de qualidade da condução consultiva.

---

## Estrutura do Projeto

```text
Projeto Tele_IA Transcricao/
│
├─ scripts_base/
│   ├─ 01_transcricao.py
│   ├─ 02_zeroshot.py
│   ├─ 03_avaliacao_zeroshot.py
│   └─ 04_painel.py
│
├─ requirements/
│   ├─ requirements_transcricao.txt
│   ├─ requirements_zero_shot.txt
│   └─ requirements_painel.txt
│
├─ arquivos_transcritos/      # não versionado
├─ saida_excel/               # não versionado
├─ saida_avaliacao/           # não versionado
│
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## Requisitos Técnicos Obrigatórios

* **Python 3.11** (obrigatório)
* Sistema Operacional: **Windows**
* Processador: CPU
* **Ollama instalado e em execução localmente (obrigatório)**

⚠️ **Este projeto NÃO utiliza VPS para execução local.**
⚠️ **Os scripts 02 e 03 dependem obrigatoriamente do Ollama local.**

---

# 🚀 EXECUÇÃO DO PROJETO — GUIA COMPLETO

## 🟢 CAMINHO RECOMENDADO (INICIANTES)

### Rodar apenas o Painel

1. Instale o Python 3.11
2. Baixe o projeto (ZIP ou git clone)
3. Crie o ambiente virtual do painel:

```powershell
py -3.11 -m venv .venv_painel
.\.venv_painel\Scripts\Activate.ps1
python -m pip install -r .\requirements\requirements_painel.txt
```

4. Execute o painel:

```powershell
streamlit run .\scripts_base\04_painel.py
```

Abra no navegador o que aparecer, exemplo:
[http://localhost:8501](http://localhost:8501)

---

## 🔵 CAMINHO COMPLETO (EXECUÇÃO MANUAL DO PIPELINE)

### 1️⃣ Etapa 01 — Transcrição de Áudio

#### Criar ambiente específico

```powershell
py -3.11 -m venv .venv_transcricao
.\.venv_transcricao\Scripts\Activate.ps1
python -m pip install -r .\requirements\requirements_transcricao.txt
```

#### Executar transcrição

```powershell
python .\scripts_base\01_transcricao.py --input_dir bd_teste_audio --model small --language pt
```

📂 Saída gerada em:

* `arquivos_transcritos/txt`
* `arquivos_transcritos/json`

---

### 2️⃣ Etapa 02 — Análise SPIN via LLM (Zero-Shot)

⚠️ **Ollama deve estar em execução**:

```bash
ollama serve
```

#### Criar ambiente Zero-Shot

```powershell
py -3.11 -m venv .venv_zeroshot
.\.venv_zeroshot\Scripts\Activate.ps1
python -m pip install -r .\requirements\requirements_zero_shot.txt
```

#### Executar análise SPIN

```powershell
python .\scripts_base\02_zeroshot.py
```

📂 Saída:

* `saida_excel/resultados_completos_SPIN.xlsx`

---

### 3️⃣ Etapa 03 — Avaliação Estruturada

Ainda no ambiente `.venv_zeroshot`:

```powershell
python .\scripts_base\03_avaliacao_zeroshot.py
```

📂 Saída:

* `saida_avaliacao/excel/avaliacao_spin_avancada.xlsx`

---

### 4️⃣ Etapa 04 — Visualização no Painel

```powershell
.\.venv_painel\Scripts\Activate.ps1
streamlit run .\scripts_base\04_painel.py
```

---

## Segurança e Ética de Dados

* Áudios não são armazenados permanentemente
* Transcrições são temporárias
* Nenhum dado sensível é persistido
* Foco exclusivo em métricas agregadas e avaliação metodológica

---

## Créditos e Autoria

### Realização Acadêmica

**Mestrado Acadêmico em Administração — Universidade Feevale**
Linha de Pesquisa: Inovação para Competitividade

### Equipe

* **Autor:** [Paulo Luis Fernandes Coutinho](https://github.com/pfcout)
* **Orientadora:** Prof.ª Dr.ª Cristiane Froehlich
* **Coorientadora:** Prof.ª Dr.ª Maria Cristina Bohnenberger
* **Colaboração Técnica:** Lucas Gabriel Ferreira Gomes (Cientista de Dados)

### Inspiração Técnica

Inspirado no motor Zero-Shot de
**Lucas Schwarz** — [https://github.com/TheLucasSchwarz/zeroshotENGINE](https://github.com/TheLucasSchwarz/zeroshotENGINE)

---

## Licença

Apache License 2.0
Uso acadêmico e profissional permitido, mantendo os devidos créditos.

---

## Considerações Finais

Este repositório foi estruturado para:

* dissertações e pesquisas aplicadas
* auditoria metodológica
* avaliação profissional de vendas consultivas
* reprodutibilidade acadêmica

Sugestões podem ser discutidas via **Issues**.
