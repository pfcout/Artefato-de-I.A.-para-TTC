# Artefato de I.A. para TTC

Este repositório apresenta um **artefato de Inteligência Artificial aplicado a TTC (Televendas Técnico-Consultivas)**, materializado em um painel acadêmico e técnico para análise automática de ligações de vendas utilizando o método **SPIN Selling**.

O sistema combina **transcrição de áudio**, **análise semântica via LLM (Zero-Shot)** e **avaliação estruturada por critérios**, com foco em reprodutibilidade, clareza metodológica e uso responsável.

---

## O que é TTC — Televendas Técnico-Consultivas

**TTC (Televendas Técnico-Consultivas)** é um modelo de vendas no qual o contato telefônico vai além da abordagem comercial tradicional, priorizando:

* diagnóstico estruturado do contexto do cliente
* entendimento técnico do problema ou necessidade
* exploração de impactos e implicações
* construção de valor antes da oferta de solução

Nesse modelo, o vendedor atua como **consultor**, guiando a conversa de forma analítica e orientada à decisão.

O método **SPIN Selling** estrutura o diálogo em **Situação, Problema, Implicação e Necessidade-Benefício**, sendo amplamente utilizado em vendas consultivas.

Este projeto utiliza IA para **avaliar objetivamente a qualidade dessas interações**, algo que tradicionalmente depende apenas de análise humana.

---

## Objetivos do projeto

O projeto foi desenvolvido com foco em:

* clareza metodológica
* reprodutibilidade acadêmica
* aplicação profissional em ambientes de TTC
* segurança de dados (não persistência de áudios e transcrições)

---

## Visão geral do funcionamento

O **SPIN Analyzer** permite avaliar ligações a partir de:

* Transcrições em texto (`[VENDEDOR]` / `[CLIENTE]`)
* Áudios WAV (transcrição automática com fallback seguro)

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
├─ scripts_base/              # Núcleo do projeto
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
├─ arquivos_transcritos/      # (não versionado)
├─ saida_excel/               # (não versionado)
├─ saida_avaliacao/           # (não versionado)
│
├─ requirements.txt           # Usado no Streamlit Cloud (somente painel)
├─ .gitignore
└─ README.md
```

> Pastas de dados, uploads e resultados **não são versionadas**, por segurança e boas práticas.

---

## Requisitos

* Python **3.11 recomendado** (compatível com 3.10)
* **Evite Python 3.13** (incompatibilidades com áudio/ASR)
* Windows (ambiente principal testado)
* CPU (GPU é opcional)
* **Ollama** configurado localmente para inferência LLM

---

## Clonar o repositório

```bash
git clone https://github.com/pfcout/Artefato-de-I.A.-para-TTC.git
cd Artefato-de-I.A.-para-TTC
```

---

## Como ativar/desativar venv 

### Ativar uma venv

```powershell
.\.venv_painel\Scripts\Activate.ps1
```

### Sair da venv

```powershell
deactivate
```

Se aparecer erro dizendo que `deactivate` não existe, significa que você **já não estava dentro** de uma venv.

---

## Rodar SOMENTE o PAINEL (recomendado para iniciantes)

> Ideal para quem quer apenas visualizar resultados e explorar o painel.

### Criar ambiente do painel

```powershell
py -3.11 -m venv .venv_painel
.\.venv_painel\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_painel.txt
```

### Executar o painel (forma correta)

```powershell
streamlit run .\scripts_base\04_painel.py
```

Abra no navegador:

```
http://localhost:8501
```

⚠️ **Nunca execute Streamlit com `python arquivo.py`.**
Sempre use `streamlit run`.

---

## Ambiente de TRANSCRIÇÃO (script 01)

> Ambiente mais sensível (Torch / áudio). Use apenas se for transcrever WAV.

```powershell
py -3.11 -m venv .venv_transcricao
.\.venv_transcricao\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel

pip uninstall -y torch torchaudio torchvision
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.2.0+cpu torchaudio==2.2.0+cpu

python -m pip install -r .\requirements\requirements_transcricao.txt
```

### Executar transcrição

```powershell
python .\scripts_base\01_transcricao.py --input_dir bd_teste_audio --model small --language pt
```

---

## Ambiente ZERO-SHOT (scripts 02 e 03)

```powershell
py -3.11 -m venv .venv_zeroshot
.\.venv_zeroshot\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r .\requirements\requirements_zero_shot.txt
```

### Análise SPIN

```powershell
python .\scripts_base\02_zeroshot.py --input_dir .\arquivos_transcritos\txt
```

### Avaliação estruturada

```powershell
python .\scripts_base\03_avaliacao_zeroshot.py --input_dir .\arquivos_transcritos\txt
```

---

## Configuração do Ollama (LLM local)

```bash
ollama serve
ollama pull llama3
```

---

## Publicar no Streamlit Cloud (somente o painel)

Este projeto está preparado para deploy **leve e estável**.

### Regras obrigatórias

* O arquivo **`requirements.txt` na raiz** deve conter:

  ```txt
  -r requirements/requirements_painel.txt
  ```
* Arquivo principal:

  ```text
  scripts_base/04_painel.py
  ```

❌ Não instale transcrição ou LLM no deploy do Streamlit.

---

## Segurança e privacidade

* Áudios não são persistidos
* Transcrições são temporárias
* Nenhum dado sensível é armazenado
* Apenas métricas agregadas podem ser salvas (opcional)

---

## Créditos

### Inspiração técnica

Projeto inspirado no motor Zero-Shot de
**Lucas Schwarz**
[https://github.com/TheLucasSchwarz/zeroshotENGINE](https://github.com/TheLucasSchwarz/zeroshotENGINE)

### Autoria

* **Criador:** Paulo Coutinho
* **Colaborador:** Lucas Gabriel Ferreira Gomes
  *(Freelancer / Cientista de Dados)*

---

## Licença

Apache License 2.0
Uso acadêmico e profissional permitido, mantendo créditos.

---

## Observações finais

Este repositório foi estruturado para:

* TCC / pesquisa aplicada
* auditoria metodológica
* boas práticas de engenharia
* compatibilidade com GitHub e Streamlit Cloud

Sugestões podem ser discutidas via **Issues**.
