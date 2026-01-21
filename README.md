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

* Python **3.11 recomendado** (compatível com 3.10+)
* Windows (ambiente principal testado)
* CPU (GPU é opcional)
* Configuração local do **Ollama** para inferência LLM

---

## Instalação — do zero

### 1. Clonar o repositório

```bash
git clone https://github.com/pfcout/Artefato-de-I.A.-para-TTC.git
cd Artefato-de-I.A.-para-TTC
```

---

### 2. Criar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

---

### 3. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Ambientes virtuais **não são versionados**.
> A reprodução do projeto é feita exclusivamente via `requirements.txt`.

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

## Execução avançada (pipeline sem interface)

Embora o **painel Streamlit** seja a forma principal e recomendada de utilização do projeto, o repositório também disponibiliza o **pipeline completo de processamento** de forma modular, por meio dos scripts localizados em `scripts_base/`.

Esses scripts permitem a execução **sem interface gráfica**, sendo úteis para:

* reprodutibilidade acadêmica
* auditoria metodológica
* experimentos controlados
* integração com outros sistemas

### Scripts principais

* `01_transcricao.py`
  Responsável pela transcrição automática de áudios (quando aplicável), incluindo diarização e pós-processamento.

* `02_zeroshot.py`
  Realiza a análise semântica das transcrições utilizando um motor Zero-Shot via LLM.

* `03_avaliacao_zeroshot.py`
  Aplica critérios estruturados de avaliação SPIN, gerando métricas e pontuações.

O script `04_painel.py` atua como **orquestrador**, encapsulando essas etapas em uma interface interativa e segura.

> Para a maioria dos usuários, recomenda-se **utilizar exclusivamente o painel**.
> A execução direta dos scripts é indicada apenas para usuários com conhecimento técnico ou fins acadêmicos específicos.

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
