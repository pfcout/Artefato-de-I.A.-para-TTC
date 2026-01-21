# 🎧 Projeto SPIN Analyzer – Painel de Avaliação de Ligações

## 🧭 Visão Geral
O **SPIN Analyzer** é um painel interativo desenvolvido em **Python (Streamlit)** para visualizar e analisar os resultados das ligações avaliadas pela metodologia **SPIN Selling**.  
Ele foi projetado para facilitar o acompanhamento de desempenho de vendedores e a qualidade das interações comerciais, utilizando os dados consolidados no arquivo:

```
dados_excel/avaliacao_spin_avancada.xlsx
```

---

## 🧩 Estrutura do Projeto

```
Projeto Tele_IA Painel/
│
├── dados_excel/
│   └── avaliacao_spin_avancada.xlsx     # Base de dados com avaliações SPIN
│
├── spin_dashboard.py                    # Painel principal (interface Streamlit)
│
└── README_Problema_Painel_SPIN.md       # Registro técnico do problema
```

---

## ⚙️ Componentes Principais

### 1. **spin_dashboard.py**
Painel principal e único ativo.  
- Desenvolvido com **Streamlit + Pandas + Pathlib**.  
- Carrega automaticamente o arquivo Excel com as análises.  
- Permite selecionar um **vendedor** e uma **ligação específica**.  
- Exibe as principais métricas:
  - **Classificação SPIN**
  - **Nota Final**
  - **Pontuação Total**
- Mostra feedbacks detalhados para:
  - Abertura  
  - Problema  
  - Implicação  
  - Necessidade (Payoff)  
  - Feedback geral consolidado  

### 2. **Planilha de Dados**
A planilha contém todas as análises produzidas pelo pipeline SPIN, incluindo colunas como:
```
arquivo, vendedor, nota_final, pontuacao_total,
classificacao_spin, abertura_feedback,
problem_feedback, implicacao_feedback,
necessidade_feedback, feedback_geral
```

---

## 🖥️ Fluxo de Uso

1. Executar o painel:
   ```bash
   streamlit run spin_dashboard.py
   ```
2. O sistema carrega o Excel automaticamente.  
3. O usuário seleciona:
   - Um vendedor (ex.: *AmandaBalboniDaSilva*)  
   - Uma ligação (ex.: *AmandaBalboniDaSilva_20250417.txt*)  
4. O painel exibe:
   - Métricas SPIN  
   - Feedbacks detalhados  
   - Interface moderna e responsiva  

---

## 🎨 Layout
O painel utiliza um estilo **visual moderno e claro**, com:
- Cards de métricas com bandas de título coloridas;  
- Blocos de feedback estilizados;  
- Rodapé institucional:  
  > “SPIN Analyzer — Projeto Tele_IA 2025 | Desenvolvido por Paulo Coutinho”.

---

## 🧱 Tecnologias Utilizadas
- **Python 3.12+**
- **Streamlit**
- **Pandas**
- **Pathlib**
- **OpenPyXL (para leitura de Excel)**  

---

## 🔧 Ambiente de Execução
- **SO:** Windows  
- **Ambiente:** `.venv` dedicado  
- **Execução local:** via `streamlit run spin_dashboard.py`

---

## 🚨 Problema Técnico Atual — *Ainda não resolvido*

### ❗ Sintoma
Ao alterar o **vendedor** ou a **ligação** nos `selectbox`, as **métricas e feedbacks não são atualizados**.  
O painel continua exibindo **sempre os dados da primeira linha** do DataFrame.

### ⚠️ Impacto
- As informações mostradas na interface **não correspondem à seleção atual**.  
- Usuários não conseguem comparar resultados de diferentes ligações.

### 🔍 Diagnóstico
- O bug está ligado ao **estado de sessão (`st.session_state`) e rerun do Streamlit**.  
- Mesmo com as chaves dinâmicas (`key=f"ligacao_sel_{vendedor_sel}"`), o rerun não força atualização dos widgets.  
- O DataFrame e o estado dos `selectbox` ficam **dessincronizados** durante a reexecução automática do Streamlit.

### 🧪 Tentativas anteriores (sem sucesso)
- Redefinição das chaves de sessão.  
- Normalização de colunas e dados.  
- Debug explícito com logs.  
- Remoção de cache e duplicatas de colunas.  
- Teste em novo ambiente `.venv`.

### 📌 Status
> **Problema persiste.**  
> A mudança de vendedor ou ligação **não atualiza os dados exibidos**.  
> Registrado oficialmente: *“O problema continua. Ou seja, o ChatGPT não consegue resolver o problema.”*

---

## 🧠 Próximos Passos Recomendados
1. Criar um **reprodutor mínimo** com 3 linhas para isolar o bug.  
2. Ativar modo **debug de reruns** do Streamlit (`st.experimental_rerun()`).  
3. Testar o painel em versão atualizada do **Streamlit 1.39+**.  
4. Verificar conflito com a manipulação do `session_state`.  
5. Caso necessário, reescrever o seletor usando **st.radio** ou **st.data_editor** para forçar re-render.

---

### 📄 Registro Oficial
Arquivo: `README_Problema_Painel_SPIN.md`  
Situação: **NÃO RESOLVIDO**  
Responsável técnico: **Paulo Coutinho**  
Última versão: **v3.9 – 2025.3**
