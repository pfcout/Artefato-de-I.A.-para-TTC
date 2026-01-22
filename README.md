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

## Como ativar/desativar venv no PowerShell (leigo-friendly)

✅ **Ativar uma venv** (exemplo):

```powershell
.\.venv_transcricao\Scripts\Activate.ps1
```

✅ **Sair da venv** (opção 1 — funciona sempre):

```powershell
deactivate
```

Se aparecer: `deactivate : O termo 'deactivate' não é reconhecido`
➡️ significa que você **já não estava dentro** de uma venv.

✅ **Sair da venv** (opção 2 — “forçado”, se quiser garantir):

* Feche o PowerShell e abra de novo na pasta do projeto.

---

### 2. Ambiente de TRANSCRIÇÃO (script 01)

> Este é o ambiente mais sensível por causa de dependências de áudio (Torch/Torchaudio).
> Para evitar erros comuns no Windows, instale Torch/Torchaudio CPU fixos antes do requirements.

```powershell
py -3.11 -m venv .venv_transcricao
.\.venv_transcricao\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel

# (IMPORTANTE) Torch/Torchaudio CPU (evita bugs de torchaudio no Windows)
pip uninstall -y torch torchaudio torchvision
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.2.0+cpu torchaudio==2.2.0+cpu

# Agora instale o resto
python -m pip install -r .\requirements\requirements_transcricao.txt
```

#### Preparar pasta de áudios (WAV)

Crie a pasta e coloque seus arquivos `.wav` lá dentro:

```powershell
mkdir bd_teste_audio
```

✅ **Exemplo**: `bd_teste_audio\01_Abertura.wav`

#### Executar (funcionando)

```powershell
python .\scripts_base\01_transcricao.py --input_dir bd_teste_audio --model small --language pt
```

✅ Saídas geradas automaticamente:

* `arquivos_transcritos\txt\`  (transcrições compatíveis com o Zero-Shot)
* `arquivos_transcritos\json\` (segmentos e logs)

---

### 3. Ambiente ZERO-SHOT (script 02 + script 03)

> Este ambiente roda a análise SPIN via LLM (Ollama) e gera planilhas Excel.

```powershell
py -3.11 -m venv .venv_zeroshot
.\.venv_zeroshot\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_zero_shot.txt
```

#### Executar script 02 (análise SPIN)

Use como entrada os TXT gerados no script 01:

```powershell
python .\scripts_base\02_zeroshot.py --input_dir .\arquivos_transcritos\txt
```

✅ Saída:

* `saida_excel\resultados_completos_SPIN.xlsx`

#### Executar script 03 (avaliação estruturada)

⚠️ Observação importante:

* O script correto é `03_avaliacao_zeroshot.py`
* `03_metricas.py` **não faz parte** desta versão do projeto.

```powershell
python .\scripts_base\03_avaliacao_zeroshot.py --input_dir .\arquivos_transcritos\txt
```

✅ Saída:

* `saida_avaliacao\excel\avaliacao_spin_avancada.xlsx`

---

### 4. Ambiente do PAINEL (script 04)

> O painel Streamlit deve ser iniciado com **streamlit run**.

```powershell
py -3.11 -m venv .venv_painel
.\.venv_painel\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_painel.txt
```

#### Executar (forma correta)

```powershell
streamlit run .\scripts_base\04_painel.py
```

Depois abra no navegador:

* `http://localhost:8501`

✅ Se aparecer aviso “missing ScriptRunContext”, normalmente é porque alguém tentou rodar com:

```powershell
python .\scripts_base\04_painel.py
```

➡️ **Não use `python` para iniciar Streamlit. Use `streamlit run`.**

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
