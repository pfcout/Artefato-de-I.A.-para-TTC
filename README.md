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

# 🚀 Como Rodar o Projeto (Guia Completo — Iniciantes e Avançados)

Esta seção explica **passo a passo**, de forma **extremamente didática**, como executar o projeto **localmente**, desde a opção mais simples (apenas o painel) até o fluxo completo de processamento (**01 → 02 → 03 → Painel**).
O texto foi escrito assumindo que o leitor **nunca programou**, **nunca usou PowerShell** e **não tem familiaridade com ambientes técnicos**.

> ⚠️ **Aviso fundamental (leia com atenção):**
> **Se o Ollama não estiver ativo, o projeto não roda corretamente.**
> O Ollama é **obrigatório** para:
>
> * executar corretamente o **painel local quando há avaliação**,
> * executar o **02_zeroshot.py**,
> * executar o **03_avaliacao_zeroshot.py**.
>
> O fluxo **local NÃO usa VPS**.

---

## 📌 Antes de começar (obrigatório)

Antes de rodar o projeto, é necessário **instalar três ferramentas básicas** no computador. Todas são gratuitas.

### 1️⃣ Python 3.11 (obrigatório)

O Python é a linguagem usada no projeto.

* Site oficial para download:
  [https://www.python.org/downloads/release/python-3110/](https://www.python.org/downloads/release/python-3110/)

Durante a instalação:

* Marque a opção **“Add Python to PATH”**
* Clique em **Install**

#### Como confirmar que o Python está instalado

1. Abra o **PowerShell** (veja abaixo como abrir).
2. Digite:

   ```powershell
   py -3.11 --version
   ```
3. O resultado esperado é algo parecido com:

   ```
   Python 3.11.x
   ```

---

### 2️⃣ Git (obrigatório para baixar o projeto)

O Git é usado para **baixar o projeto do GitHub**.

* Site oficial:
  [https://git-scm.com/downloads](https://git-scm.com/downloads)

Instale aceitando as opções padrão.

#### Como confirmar que o Git está instalado

No PowerShell, digite:

```powershell
git --version
```

Resultado esperado:

```
git version x.xx.x
```

---

### 3️⃣ Ollama (OBRIGATÓRIO)

O Ollama é o motor de **Inteligência Artificial local (LLM)** usado pelo projeto.

* Site oficial:
  [https://ollama.com/download](https://ollama.com/download)

Após instalar, **o Ollama precisa estar ativo** sempre que você for:

* rodar o painel local,
* rodar o script 02,
* rodar o script 03.

#### Como confirmar que o Ollama está instalado

No PowerShell:

```powershell
ollama --version
```

#### Como iniciar o Ollama (passo obrigatório)

Abra **uma janela separada do PowerShell** e execute:

```powershell
ollama serve
```

✅ **Essa janela deve permanecer aberta** enquanto o projeto estiver sendo usado.
Ela indica que o serviço de IA está ativo.

---

## 💻 O que é terminal e PowerShell (explicação simples)

* **Terminal / PowerShell** é uma janela onde você digita comandos.
* No Windows:

  1. Clique no botão **Iniciar**
  2. Digite **PowerShell**
  3. Clique para abrir

Durante este guia, **todos os comandos devem ser digitados no PowerShell**.

---

## 📥 Baixar o projeto

Você pode baixar o projeto de duas formas.

### Opção 1 — Baixar como ZIP (mais simples para iniciantes)

1. Acesse o repositório no GitHub.
2. Clique no botão **Code**.
3. Clique em **Download ZIP**.
4. Extraia o arquivo ZIP.
5. Abra a pasta extraída — esta será a pasta do projeto.

---

### Opção 2 — Baixar via Git (recomendado)

No PowerShell, digite:

```powershell
git clone https://github.com/pfcout/Artefato-de-I.A.-para-TTC.git
cd Artefato-de-I.A.-para-TTC
```

📌 O comando `cd` significa **“entrar na pasta”**.

---

## 🧪 O que é venv e por que usamos aqui

Uma **venv (ambiente virtual)** é um ambiente isolado de Python usado para evitar conflitos entre bibliotecas.

Este projeto utiliza **três ambientes separados**, porque cada etapa tem dependências diferentes:

* `.venv_painel` → para o painel (04)
* `.venv_transcricao` → para transcrição de áudio (01)
* `.venv_zeroshot` → para análise e avaliação (02 e 03)

---

## 🪟 Regra importante: 1 janela por tarefa

Use sempre:

* **Uma janela do PowerShell** para rodar comandos do projeto
* **Uma segunda janela do PowerShell** exclusivamente para manter:

  ```powershell
  ollama serve
  ```

---

# 🟢 Caminho A — Apenas Painel (iniciante absoluto)

Este é o caminho **recomendado para iniciantes**.

### Passo 1 — Entrar na pasta do projeto

No PowerShell:

```powershell
cd caminho\da\pasta\Artefato-de-I.A.-para-TTC
```

---

### Passo 2 — Criar o ambiente do painel

```powershell
py -3.11 -m venv .venv_painel
```

---

### Passo 3 — Ativar o ambiente

```powershell
.\.venv_painel\Scripts\Activate.ps1
```

Quando ativado, o terminal mostrará algo como:

```
(.venv_painel)
```

---

### Passo 4 — Atualizar ferramentas básicas

```powershell
python -m pip install -U pip setuptools wheel
```

---

### Passo 5 — Instalar dependências do painel

```powershell
python -m pip install -r requirements\requirements_painel.txt
```

---

### Passo 6 — Iniciar o painel

```powershell
streamlit run scripts_base\04_painel.py
```

O navegador abrirá automaticamente em:

```
http://localhost:8501
```

Para parar o painel:

* Pressione **Ctrl + C** no PowerShell.

---

# 🔵 Caminho B — Pipeline Completo Manual (01 → 02 → 03 → Painel)

## Etapa 01 — Transcrição de áudio

* Crie o ambiente:

  ```powershell
  py -3.11 -m venv .venv_transcricao
  ```
* Ative:

  ```powershell
  .\.venv_transcricao\Scripts\Activate.ps1
  ```
* Instale dependências:

  ```powershell
  python -m pip install -r requirements\requirements_transcricao.txt
  ```
* Coloque arquivos WAV na pasta:

  ```
  bd_teste_audio/
  ```
* Execute:

  ```powershell
  python scripts_base\01_transcricao.py --input_dir bd_teste_audio --model small --language pt
  ```

📄 Saída esperada:

```
arquivos_transcritos/txt/
arquivos_transcritos/json/
```

---

## Etapa 02 — Análise SPIN (Ollama obrigatório)

⚠️ **Ollama deve estar ativo (`ollama serve`)**.

* Crie o ambiente:

  ```powershell
  py -3.11 -m venv .venv_zeroshot
  ```
* Ative:

  ```powershell
  .\.venv_zeroshot\Scripts\Activate.ps1
  ```
* Instale dependências:

  ```powershell
  python -m pip install -r requirements\requirements_zero_shot.txt
  ```
* Execute:

  ```powershell
  python scripts_base\02_zeroshot.py
  ```

📊 Saída:

```
saida_excel/resultados_completos_SPIN.xlsx
```

---

## Etapa 03 — Avaliação estruturada (Ollama obrigatório)

Com o Ollama ainda ativo:

```powershell
python scripts_base\03_avaliacao_zeroshot.py
```

📊 Saída:

```
saida_avaliacao/excel/avaliacao_spin_avancada.xlsx
```

---

## Etapa 04 — Painel local

Ative o ambiente do painel:

```powershell
.\.venv_painel\Scripts\Activate.ps1
```

Execute:

```powershell
streamlit run scripts_base\04_painel.py
```

---

# 🟡 Caminho C — Rodar apenas partes específicas

* **Quero só transcrever (01):**
  Use apenas `.venv_transcricao` e o script 01.

* **Já tenho TXT e quero rodar 02 e 03:**
  Use `.venv_zeroshot`, mantenha o Ollama ativo e rode 02 → 03.

* **Quero apenas visualizar resultados:**
  Use apenas `.venv_painel` e o painel. (ollama ativo)

---

## 🌐 Painel Online (Streamlit Cloud)

Para **demonstração rápida**, **auditoria visual** ou acesso sem instalação local:

👉 [https://artefato-de-ia-para-ttc-cqiwcwa9yam3osormngbju.streamlit.app](https://artefato-de-ia-para-ttc-cqiwcwa9yam3osormngbju.streamlit.app)

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
