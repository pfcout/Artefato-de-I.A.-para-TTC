# Artefato de Inteligência Artificial para Televendas Técnico-Consultivas (TTC)

Este repositório apresenta um **artefato acadêmico de Inteligência Artificial**, desenvolvido como objeto de estudo do **Mestrado Acadêmico em Administração da Universidade Feevale**, com foco na **Inteligência Comercial aplicada a Televendas Técnico-Consultivas (TTC)**.

O artefato materializa-se em um **pipeline completo de análise automática de ligações de vendas**, integrando:

* **Transcrição automática de áudio**
* **Análise semântica via Modelos de Linguagem (LLM) em modo Zero-Shot**
* **Avaliação estruturada baseada no método SPIN Selling (Rackham, 1988)**

O projeto foi concebido para atender simultaneamente a **rigor científico**, **aplicabilidade organizacional** e **reprodutibilidade metodológica**, respeitando princípios de **segurança, ética e uso responsável de dados**.

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

O artefato opera por meio de um fluxo local em Windows, com execução manual do pipeline:

1. Transcrição de áudio (geração de TXT e JSON)
2. Análise SPIN via LLM em modo Zero-Shot (geração de Excel)

---

## Arquitetura do Artefato

O sistema foi construído sobre dois pilares fundamentais:

1. **Transcrição de Áudio**
   Conversão de chamadas telefônicas (WAV) em texto estruturado (TXT) e metadados (JSON).

2. **Análise Semântica via LLM (Zero-Shot)**
   Classificação automática das falas segundo as fases do SPIN Selling, sem treinamento supervisionado, com geração de planilhas Excel para auditoria e uso organizacional.

---

## Requisitos Técnicos Obrigatórios

* **Python 3.11** (obrigatório)
* Sistema Operacional: **Windows**
* Processador: CPU
* **Ollama instalado e em execução localmente (obrigatório)**

⚠️ **Este projeto NÃO utiliza VPS para execução local.**
⚠️ **O script 02 depende obrigatoriamente do Ollama local (qwen14b).**

---

# 🚀 Como Rodar o Projeto (Guia Completo — Iniciantes e Avançados)

Esta seção explica, passo a passo e de forma didática, como executar o projeto **localmente no Windows**, utilizando **PowerShell** (e, opcionalmente, **VS Code**), no fluxo **01 → 02**.

O texto foi escrito assumindo que o leitor nunca programou, nunca usou PowerShell e não tem familiaridade com ambientes técnicos.

> Aviso fundamental:
> Se o **Ollama** não estiver ativo, o projeto não executa corretamente a etapa **02_zeroshot.py**.
> O fluxo local **não utiliza VPS**.

---

## 📌 Antes de começar (obrigatório)

Antes de rodar o projeto, instale as ferramentas abaixo. Todas são gratuitas.

### 1) Python 3.11 (obrigatório)

O Python é a linguagem usada no projeto.

Link oficial (Python 3.11):
[https://www.python.org/downloads/release/python-3110/](https://www.python.org/downloads/release/python-3110/)

Durante a instalação:

* Marque a opção **Add Python to PATH**
* Conclua a instalação

Como confirmar no PowerShell:

```powershell
py -3.11 --version
```

Resultado esperado (exemplo):

```
Python 3.11.x
```

---

### 2) Git (obrigatório para clonar o repositório)

O Git é usado para baixar o projeto do GitHub.

Link oficial:
[https://git-scm.com/downloads](https://git-scm.com/downloads)

Como confirmar no PowerShell:

```powershell
git --version
```

---

### 3) Ollama (obrigatório para a etapa 02)

O Ollama é o motor local de LLM usado pela etapa 02.

Link oficial:
[https://ollama.com/download](https://ollama.com/download)

Como confirmar no PowerShell:

```powershell
ollama --version
```

Como iniciar o Ollama no Windows (passo obrigatório):

1. Abra **uma segunda janela** do PowerShell.
2. Execute:

```powershell
ollama serve
```

Essa janela deve permanecer aberta enquanto você estiver executando a etapa 02.

Modelo obrigatório (local):

* O script 02 utiliza o modelo configurado por variável de ambiente `OLLAMA_MODEL`.
* Valor esperado neste projeto: `qwen2.5:14b-instruct-q4_K_M`

Opcionalmente, você pode definir no PowerShell (na janela onde rodará o script 02):

```powershell
$env:OLLAMA_MODEL="qwen2.5:14b-instruct-q4_K_M"
```

---

## 💻 O que é terminal e PowerShell

PowerShell é uma janela onde você digita comandos.

Para abrir no Windows:

1. Clique no menu Iniciar
2. Digite **PowerShell**
3. Abra o aplicativo

Durante este guia, todos os comandos devem ser executados no PowerShell.

---

## 📥 Baixar o projeto (clonar via Git)

No PowerShell, execute:

```powershell
git clone https://github.com/pfcout/Artefato-de-I.A.-para-TTC.git
cd Artefato-de-I.A.-para-TTC
```

Observação:

* O comando `cd` significa “entrar na pasta”.

---

## 🧪 O que é venv e por que usamos

Uma **venv** (ambiente virtual) é um ambiente isolado do Python. Ela evita conflitos entre bibliotecas de projetos diferentes.

Este projeto utiliza **dois ambientes separados**, porque as dependências de transcrição (01) são diferentes das dependências de análise (02):

* `.venv_transcricao` para o script 01
* `.venv_zeroshot` para o script 02

---

## 🪟 Regra importante: use duas janelas

Use sempre:

* Janela 1: comandos do projeto (01 e 02)
* Janela 2: manter o Ollama ativo com `ollama serve` (apenas para a etapa 02)

---

# 🟦 Etapa 01 — Transcrição local (scripts_base/01_transcricao.py)

## 1) Criar e ativar o ambiente da transcrição

Na pasta do projeto, execute:

```powershell
py -3.11 -m venv .venv_transcricao
.\.venv_transcricao\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
```

Quando ativado, o terminal mostrará algo como `(.venv_transcricao)` no início da linha.

## 2) Instalar dependências da transcrição

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements\requirements_transcricao.txt
```

## 3) Preparar os arquivos de entrada

Coloque seus áudios `.wav` na pasta indicada pelo comando `--input_dir`.

Exemplo de pasta utilizada no projeto:

* `arquivos_audio/`

## 4) Executar a transcrição (exemplo PowerShell com quebras de linha)

Exemplo para processar todos os `.wav` da pasta `arquivos_audio`:

```powershell
python .\scripts_base\01_transcricao.py `
  --input_dir ".\arquivos_audio" `
  --pattern "*.wav" `
  --recursive true `
  --model large-v3 `
  --language pt `
  --beam_size 5 `
  --vad_filter true `
  --device auto
```

Observações importantes:

* `--device auto` tenta usar GPU se existir e, caso contrário, usa CPU automaticamente.
* `HF_TOKEN` é opcional. Se não estiver configurado (ou se falhar), o script deve finalizar **sem travar**, gerando as saídas com fallback.

## 5) Saídas esperadas após a etapa 01

Após rodar, você deve ver:

* `arquivos_transcritos/txt/` com arquivos `.txt`
* `arquivos_transcritos/json/` com arquivos `.json`

Checklist:

* Existe `arquivos_transcritos/txt/<nome_do_audio>.txt`
* Existe `arquivos_transcritos/json/<nome_do_audio>.json`

---

# 🔐 Diarização opcional com pyannote (HF_TOKEN)

A diarização (separação de falas por participantes) é opcional e depende do `HF_TOKEN` e do aceite dos termos do modelo no Hugging Face.

## 1) Criar conta no Hugging Face

Acesse:
[https://huggingface.co/](https://huggingface.co/)

Crie uma conta e faça login.

## 2) Gerar um Access Token (HF_TOKEN)

Acesse a página oficial de tokens:
[https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

Crie um token e copie o valor.

## 3) Aceitar os termos do modelo pyannote

A diarização depende do modelo:
[https://huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

Ao acessar essa página logado:

* Leia os termos/licença do modelo
* Clique para aceitar/requisitar acesso, quando o Hugging Face solicitar

Sem esse aceite, o Hugging Face pode bloquear o download (acesso “gated”).

## 4) Configurar HF_TOKEN no PowerShell (temporário)

Na janela do PowerShell onde você executará o script 01:

```powershell
$env:HF_TOKEN="COLE_AQUI_SEU_TOKEN"
```

Esse método vale apenas para a janela atual. Ao fechar o PowerShell, a variável é perdida.

## 5) Configurar HF_TOKEN permanente no Windows (Variáveis de Ambiente)

1. Abra o menu Iniciar e procure por **Editar as variáveis de ambiente do sistema**
2. Clique em **Variáveis de Ambiente**
3. Em **Variáveis do usuário** (ou do sistema, se preferir), clique em **Novo**
4. Defina:

   * Nome da variável: `HF_TOKEN`
   * Valor da variável: seu token
5. Confirme e reinicie o PowerShell

## 6) Executar novamente a etapa 01 com HF_TOKEN

Com o token configurado, execute novamente o 01 normalmente.
Se o modelo estiver autorizado, a diarização será tentada automaticamente.

---

## Erros comuns (HF_TOKEN / pyannote)

### 1) HF_TOKEN ausente

Sintoma:

* O script executa e gera as saídas, mas não realiza diarização.

Ação:

* Defina `HF_TOKEN` e tente novamente.

### 2) Acesso gated não aceito (termos não aceitos)

Sintoma:

* Erros relacionados a acesso negado no download do modelo.

Ação:

* Acesse a página do modelo e aceite/requisite acesso:
  [https://huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

### 3) Token inválido

Sintoma:

* Erros indicando falha de autenticação.

Ação:

* Gere um novo token:
  [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
* Atualize o `HF_TOKEN` no PowerShell ou nas variáveis do Windows.

### 4) pyannote retornando “single speaker”

Sintoma:

* A diarização indica apenas um participante, ou o resultado final concentra falas em um único papel.

Contexto:

* Isso pode ocorrer em áudios curtos, com falas sobrepostas, baixa qualidade, ou quando o diarizador não separa corretamente e em chats de ia.

Comportamento esperado do projeto:

* O script deve **continuar sem travar** e gerar saídas em modo fallback quando a diarização não for considerada confiável.

---

# 🟩 Etapa 02 — Análise SPIN Zero-Shot via Ollama (scripts_base/02_zeroshot.py)

A etapa 02 lê os TXT gerados pela etapa 01 e produz planilhas Excel com o resultado da análise SPIN.

Pré-requisito obrigatório:

* O Ollama deve estar ativo na máquina com:

```powershell
ollama serve
```

## 1) Criar e ativar o ambiente do zero-shot

Na pasta do projeto:

```powershell
py -3.11 -m venv .venv_zeroshot
.\.venv_zeroshot\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
```

## 2) Instalar dependências do zero-shot

```powershell
python -m pip install -r requirements\requirements_zero_shot.txt
```

## 3) Executar a análise SPIN (exemplo PowerShell)

Exemplo usando os caminhos padrão do projeto (entrada em `arquivos_transcritos/txt` e saída em `saida_excel`):

```powershell
$env:OLLAMA_MODEL="qwen2.5:14b-instruct-q4_K_M"

python .\scripts_base\02_zeroshot.py `
  --in_dir ".\arquivos_transcritos\txt" `
  --out_dir ".\saida_excel" `
  --pattern "*.txt" `
  --recursive true `
  --workers 1
```

Observações:

* O script 02 lê prompts a partir de arquivos em `assets/`:

  * `assets/Command_Core_D_Check_V2_6.txt`

## 4) Saídas esperadas após a etapa 02

Após rodar, você deve ver:

* `saida_excel/` contendo arquivos Excel gerados para cada transcrição (por exemplo: `*_SPIN.xlsx`)

Checklist:

* Existe a pasta `saida_excel/`
* Há arquivos `*_SPIN.xlsx` compatíveis com os TXT processados

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
* **Colaboração Técnica:** [Lucas Gabriel Ferreira Gomes (Cientista de Dados)](https://github.com/Oreki820)

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
