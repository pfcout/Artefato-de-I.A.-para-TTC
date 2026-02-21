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
# SPIN Analyzer

## `scripts_base/01_transcricao.py`

### Pipeline de Transcrição Robusta para Análise de Ligações Comerciais

---

## Visão Geral

O `01_transcricao.py` é o pipeline principal de transcrição robusta do **SPIN Analyzer**, sistema de análise de ligações comerciais baseado em:

* Transcrição automática de áudio (ASR)
* Identificação de papéis (VENDEDOR / CLIENTE)
* Estruturação de dados para análises posteriores

O script foi projetado com foco explícito em **robustez operacional absoluta**.

Ele:

* Executa ASR com **`faster-whisper`**
* Opcionalmente executa diarização com **`pyannote/speaker-diarization-3.1`**
* Sempre gera saída TXT e JSON
* Nunca quebra o pipeline por falhas externas
* Possui cache inteligente com SQLite
* Arquiva áudios processados
* Possui fallback textual caso diarização falhe
* Implementa sistema híbrido de definição de papéis
* Garante previsibilidade operacional em ambiente Windows

Este script é considerado o pipeline de produção resiliente do SPIN Analyzer.

---

## Arquitetura do Pipeline

### Fluxo Geral

1. Descoberta de áudios em `arquivos_audio/`
2. Cálculo de hash SHA256 do áudio
3. Cálculo de hash dos parâmetros relevantes do ASR
4. Geração de `cache_key = sha256(audio) + sha256(params)`
5. Consulta ao banco `crachedbl/cache.db`

### Caso Cache HIT

* Não reprocessa o áudio
* Regera arquivos TXT e JSON a partir do banco
* Move o áudio para `crachedbl/`
* Finaliza rapidamente sem custo computacional

### Caso Cache MISS

Pipeline completo:

1. Execução do ASR (`faster-whisper`)
2. Merge inteligente de segmentos
3. Split de turnos mistos
4. Correção lexical via dicionário
5. Diarização opcional (pyannote)
6. Avaliação de qualidade da diarização
7. Se diarização falhar → `role_by_text`
8. Smoothing de papéis
9. Geração de TXT final
10. Geração de JSON estruturado
11. Persistência no cache
12. Arquivamento do áudio em `crachedbl/`

O pipeline é linear, determinístico e sempre termina com geração de saída.

---

## Sistema de Cache Inteligente

### Estrutura

* Pasta obrigatória: `arquivos_historico_audio/`
* Banco SQLite: `arquivos_historico_audio/cache.db`

### Cache Key

```
sha256(audio_bytes) + sha256(params_relevantes)
```

Os parâmetros relevantes incluem:

* Modelo ASR
* Device
* Compute type
* Beam size
* VAD
* Linguagem

### Comportamento

* Se já processado e sem `--force`:

  * Não reprocessa
  * Regera saídas do banco
* Após processamento:

  * Áudio é movido para `arquivos_historico_audio/`
  * Conteúdo TXT/JSON é armazenado no SQLite

### Benefícios

* Redução drástica de custo GPU/CPU
* Reprodutibilidade garantida
* Eliminação de processamento redundante
* Previsibilidade operacional
* Idempotência do pipeline

Permite forçar reprocessamento com:

```
--force
```

---

## ASR — Faster Whisper

Motor de transcrição baseado em `faster-whisper`.

### Modelo

Configurável via CLI
Default: `large-v3`

### Device

```
--device auto  → usa CUDA se disponível
--device cuda  → tenta CUDA, fallback para CPU
--device cpu   → força CPU
```

### Compute Type

* GPU → `float16`
* CPU → `int8`

### Recursos

* VAD opcional
* Beam search configurável
* Heartbeat de progresso
* Tratamento completo de exceções

O ASR nunca deve travar o pipeline. Qualquer falha é capturada e registrada.

---

## Merge Inteligente de Segmentos

Problema: o ASR pode gerar fragmentação excessiva.

Solução: merge heurístico baseado em:

* Gap máximo entre segmentos
* Ausência de pontuação final
* Continuidade textual
* Limite máximo de caracteres

Benefícios:

* Melhora legibilidade
* Reduz ruído estrutural
* Aumenta qualidade da classificação de papéis
* Evita linhas artificialmente quebradas

---

## Split de Turnos Mistos

Detecta frases compostas como:

> "Perfeito. Pode me confirmar o CNPJ?"

Processo:

* Divide por sentença
* Redistribui timestamps proporcionalmente
* Limita número máximo de splits por segmento

Impacto:

* Reduz casos de VENDEDOR e CLIENTE na mesma linha
* Melhora precisão da classificação híbrida

---

## Diarização (Opcional)

Modelo utilizado:

`pyannote/speaker-diarization-3.1`

Requisitos:

* `HF_TOKEN`
* Dependências instaladas

### Garantias

* Nunca pode quebrar o pipeline
* Falhas são capturadas
* Pipeline continua via fallback textual

### Avaliação de Qualidade

Critérios:

* `DIAR_COLLAPSE_MAX_SHARE`
* `DIAR_MIN_COVERAGE`

Se:

* Apenas 1 speaker detectado
* > 90% do tempo em um speaker
* Cobertura insuficiente

→ Diarização é considerada inválida
→ Fallback textual é acionado

Diarização é tratada como melhoria, nunca como dependência crítica.

---

## Fallback Textual — `role_by_text`

Quando diarização falha, entra o sistema textual híbrido.

Arquivos:

* `assets/roles_vendor_patterns.txt`
* `assets/roles_client_patterns.txt`

Suporte a:

* Regex
* Substring
* Fuzzy matching (rapidfuzz / fuzzywuzzy)

### Lógica

* Score para vendedor
* Score para cliente
* Heurísticas adicionais:

  * Perguntas → tendem a vendedor
  * Respostas curtas → tendem a cliente
  * Pós-pergunta forte → ajuste contextual
  * Frases de condução → reforço vendedor

Calcula:

* `vendor_score`
* `client_score`
* `role_conf`

Garante continuidade mesmo sem diarização.

---

## Smoothing de Papéis

Etapa pós-classificação.

Remove:

* “Ilhas” (ex: VENDEDOR entre dois CLIENTE)
* Inconsistências pós-pergunta forte

Usa limiar:

```
ROLE_STRONG_MIN
```

Aumenta consistência narrativa da conversa.

---

## Saídas Garantidas

Sempre gera:

* TXT → `arquivos_transcritos/txt`
* JSON → `arquivos_transcritos/json`

### Estrutura do JSON

```json
{
  "meta": {...},
  "segments": [...],
  "roles": {...},
  "stats": {...},
  "errors": [...]
}
```

Contém:

* Metadados do processamento
* Segmentos com timestamps
* Papéis atribuídos
* Estatísticas agregadas
* Erros capturados (sem quebrar execução)

---

## Garantias de Robustez

O script garante:

* Nunca quebra por ausência de HF_TOKEN
* Nunca quebra por erro de diarização
* Nunca falha silenciosamente
* Sempre produz saída
* Logs detalhados por etapa
* Heartbeat de progresso
* Tratamento extensivo de exceções
* Pipeline determinístico

Foi projetado para rodar em ambiente Windows com previsibilidade.

---

## Estrutura de Pastas

```
arquivos_audio/          → áudios brutos
arquivos_transcritos/    → saídas finais
  ├── txt/
  └── json/
assets/                  → dicionários e padrões
crachedbl/               → cache + áudios arquivados
scripts_base/            → scripts principais
```

---

#  Filosofia do Design

Este script foi construído com foco em:

* Robustez > elegância
* Reprodutibilidade
* Previsibilidade operacional
* Redução de custo computacional
* Idempotência
* Resiliência a falhas externas
* Operação estável em ambiente Windows

Cada dependência externa é tratada como potencial ponto de falha.

O sistema foi desenhado para continuar operando mesmo sob degradação parcial.

---

## Conclusão Técnica

O `01_transcricao.py` é o pipeline de produção robusto do SPIN Analyzer.

Ele foi projetado para:

* Operar de forma resiliente
* Manter consistência estrutural
* Minimizar custo computacional
* Garantir saída sempre disponível
* Proteger o sistema contra falhas de diarização e dependências externas

Trata-se de um pipeline orientado à confiabilidade operacional, preparado para uso contínuo em ambiente real de produção.

---

# SPIN Analyzer — `scripts_base/02_zeroshot.py`

## Visão Geral

O `02_zeroshot.py` é o módulo de avaliação automática SPIN do projeto **SPIN Analyzer**.
Ele representa a segunda etapa do pipeline:

```
TXT transcrito → LLM (Ollama local) → TSV estruturado → Excel individual por ligação
```

Responsabilidades principais:

* Ler arquivos `.txt` previamente transcritos.
* Enviar o conteúdo ao modelo local via Ollama.
* Exigir saída estritamente no formato TSV.
* Canonicalizar a saída para um padrão fixo.
* Gerar um Excel individual por ligação.
* Utilizar cache determinístico baseado em SQLite.
* Arquivar automaticamente o TXT processado.
* Garantir que o pipeline nunca quebre operacionalmente.

O módulo foi projetado para execução local em Windows, com foco em previsibilidade operacional, determinismo e tolerância a variações do modelo.

---

## Arquitetura Geral do Fluxo

### 2.1 Descoberta de Arquivos

* Varre a pasta de entrada (`--in_dir`)
* Suporta busca recursiva (`--recursive`)
* Filtra por padrão (`--pattern`, default `*.txt`)

### 2.2 Preparação do Texto

1. Leitura do TXT.
2. Aplicação opcional de Vendor-only filtering.
3. Limitação de tamanho:

   * Máximo de linhas (`SPIN_MAX_LINES_TOTAL`)
   * Máximo de caracteres (`SPIN_MAX_CHARS_TOTAL`)
4. Geração de `text_sha256` do texto final enviado ao LLM.
5. Geração de `prompt_sha256`.
6. Construção da cache key determinística:

```
spin02|v8_1_1|<model>|prompt=<sha>|text=<sha>|vendor_only=<0/1>
→ sha256 final
```

### 2.3 Consulta ao Cache SQLite

Se `--force` não estiver ativo:

* Consulta pelo `cache_key`.

#### Cache HIT (status=ok)

* Reconstrói Excel a partir do TSV canônico armazenado.
* Move TXT para `arquivos_historico_texto/`.
* Não executa LLM.

#### Cache MISS

* Executa Ollama.
* Realiza parsing tolerante.
* Se ALL-ZERO → executa prompt alternativo.
* Canonicaliza TSV.
* Salva no cache.
* Gera Excel.
* Move TXT para archive.

O pipeline é idempotente e determinístico.
Para o mesmo texto + prompt + modelo + flag vendor-only, o resultado é reproduzível.

---

## Integração com Ollama

A comunicação é feita via HTTP direto para:

```
/api/generate
```

Configurações via variáveis de ambiente:

* `OLLAMA_MODEL`
* `OLLAMA_URL`
* `OLLAMA_TIMEOUT_S`
* `OLLAMA_NUM_CTX`
* `OLLAMA_TEMPERATURE`
* `OLLAMA_NUM_PREDICT`
* `OLLAMA_TOP_P`
* `OLLAMA_REPEAT_PENALTY`

### Estratégias de Estabilidade

* `temperature = 0.0` (determinismo)
* `stop tokens` definidos
* `stream = False` (sem dependência de streaming)
* Retry controlado
* Timeout configurável
* Heartbeat periódico para evitar sensação de travamento

A temperatura zero é essencial para estabilidade de avaliação, evitando variação estrutural na saída TSV e reduzindo divergência entre execuções.

---

## Engenharia de Prompt

O prompt nunca é hardcoded.

Sempre é lido de:

```
assets/Command_Core_D_Check_V2_6.txt
```

Substituições dinâmicas:

* `{NOME_DO_ARQUIVO_ANEXADO}`
* `{DATA_ANALISE}`

O prompt exige explicitamente:

* 1 header TSV
* 5 linhas (P0 a P4)
* Nenhum texto adicional

Esse design reduz variabilidade estrutural do modelo e força saída alinhada ao parser.

---

## Parsing TSV Tolerante

O modelo pode retornar variações como:

* Tabs
* Espaços múltiplos
* Pipes (`|`)
* Coluna extra RESULTADO
* Sem header
* Texto extra antes/depois

O parser:

* Remove lixo textual.
* Detecta fases `P0_abertura` a `P4_need_payoff`.
* Extrai apenas valores `0` ou `1`.
* Converte `true/false`, `1.0`, etc.
* Ignora colunas extras.
* Reconstrói TSV canônico fixo:

```
SPIN SELLING    CHECK_01    CHECK_02
P0_abertura     0/1         0/1
...
```

Exige todas as 5 fases.
Se faltar qualquer fase → falha controlada.

Esse mecanismo torna o sistema robusto contra pequenas variações do LLM.

---

## Cache Determinístico (SQLite)

Banco:

```
cache_spin02/cache.db
```

Cache key inclui:

* Versão do script
* Modelo
* Hash do prompt
* Hash do texto final
* Flag vendor-only

Estrutura armazenada:

* `status` (ok/fail)
* `tsv_raw`
* `error`
* `timestamp`
* `text_sha256`
* `prompt_sha256`
* `model`

Garantias:

* Reprodutibilidade
* Economia de GPU/CPU
* Reexecução instantânea
* Proteção contra alterações acidentais

---

## Geração de Excel

Um Excel por ligação:

```
<arquivo>_SPIN.xlsx
```

Planilha única (`Planilha1`).

Estrutura:

| Coluna | Conteúdo        |
| ------ | --------------- |
| A      | Fase            |
| B      | CHECK_01        |
| C      | CHECK_02        |
| D      | RESULTADO TEXTO |

Valores:

* Normalizados para inteiro (0 ou 1)
* RESULTADO TEXTO:

  * IDÊNTICO
  * DIFERENTE

O Excel é sempre gerado — inclusive em falhas.

---

## Vendor-Only Mode

Controlado por:

```
SPIN_VENDOR_ONLY
```

Quando ativo:

* Extrai apenas falas marcadas como:

  * VENDEDOR
  * AGENTE
  * ATENDENTE
* Ignora CLIENTE.

Benefícios:

* Reduz ruído.
* Diminui tokens.
* Aumenta consistência da avaliação.
* Reduz custo computacional.

---

## Arquivamento Automático

Após processamento:

* TXT é movido para `arquivos_historico_texto/`.
* Estrutura relativa é preservada.
* Se já existir, adiciona timestamp.

Isso evita reprocessamento acidental e mantém histórico.

---

## CLI

Argumentos disponíveis:

```
--in_dir
--out_dir
--pattern
--recursive
--workers
--force
--quiet
```

### Multi-thread

Se `--workers > 1`:

* Usa `ThreadPoolExecutor`.
* Processa arquivos em paralelo.
* Mantém controle de progresso e ETA.

---

## Garantias de Robustez

O sistema:

* Nunca quebra por erro do modelo.
* Nunca quebra por parsing inválido.
* Sempre gera Excel.
* Sempre registra erro.
* Sempre salva no cache.
* Nunca depende de streaming.
* Nunca depende de GPU específica.
* Opera totalmente offline via Ollama.

---

## Controle de Custo Computacional

Mecanismos de controle:

* Cache reduz chamadas ao LLM.
* Vendor-only reduz tokens.
* Limite de linhas e caracteres.
* Temperatura zero evita divergência.
* Prompt alternativo executa apenas quando necessário.
* Reexecução por cache é instantânea.

---

## Filosofia de Design

O `02_zeroshot.py` foi projetado com foco em:

* Determinismo
* Tolerância a variações do LLM
* Segurança operacional
* Reprocessamento previsível
* Compatibilidade total com Windows
* Operação offline via Ollama
* Idempotência estrutural

Ele assume que modelos são probabilísticos e potencialmente inconsistentes, e constrói uma camada determinística acima deles.

---

## Conclusão Técnica

O `02_zeroshot.py` é o módulo de avaliação automatizada determinística do SPIN Analyzer.

Ele transforma um modelo generativo probabilístico em um componente previsível, auditável e resiliente de produção, garantindo que:

* A avaliação SPIN seja reproduzível.
* O pipeline nunca interrompa.
* O custo computacional seja controlado.
* A operação seja estável em ambiente Windows local.

É um módulo arquitetado para confiabilidade operacional mesmo sob comportamento imprevisível do modelo.

---

# Perguntas_SPIN

Esta seção apresenta perguntas de caráter exemplificativo, concebidas como referência metodológica para a aplicação dos princípios do **SPIN Selling**. 

O objetivo é fornecer suporte conceitual e orientações analíticas, sem pretender esgotar o tema ou representar um conjunto definitivo. Dessa forma, esta seção funciona como um instrumento pedagógico e de consulta, auxiliando na compreensão da estrutura e da lógica que orientam a formulação de questionamentos estratégicos dentro do contexto de vendas consultivas.

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

Se nao funcionar faça esse outro caminho:

1) Instale o Python pelo instalador “Windows installer (64-bit)” (.exe)

Vá ao site oficial do Python ([python.org](https://www.python.org/downloads/)) → Downloads → Windows

Baixe Windows installer (64-bit) (arquivo .exe)

Rode o instalador e marque:

✅ Add python.exe to PATH

(Opcional) ✅ Install for all users (se quiser)

3) Confirme que ficou OK

Abra um novo Prompt/PowerShell e rode:

```powershell
python --version
pip --version
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
* Valor esperado neste projeto: `qwen2.5:14b-instruct-q4_K_M` pode optar pro outro modelo, mas o resultado não e garantido para modelos inferiores.

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

Pasta utilizada no projeto:

* `arquivos_audio/`

## 4) Executar a transcrição (exemplo PowerShell com quebras de linha)

Exemplo para processar todos os `.wav` da pasta `arquivos_audio`:
(token e opcional, mas altamente recomendado)

```powershell
$env:HF_TOKEN="COLE_AQUI_SEU_TOKEN"
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

Antes de Aplicar atualizações em outra venv saia da antiga para evitar erros:

```powershell
deactivate
```

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
