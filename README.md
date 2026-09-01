# EduAccess - Adaptação Multimodal de Materiais com IA

## 📌 Sobre o Projeto

O **EduAccess Pro** faz parte do Projeto Viva! Universidade 2025: Ampliando a utilização de um ambiente computacional de aprendizagem para pessoas com deficiência. Ele é uma ferramenta de adaptação de materiais didáticos alimentada por Inteligência Artificial (Google Gemini) e regras heurísticas (Regex).

Esta aplicação atua como um "motor" de acessibilidade complementar ao Engenho Academy (plataforma interativa legada de 2024), automatizando a adequação de PDFs e textos de disciplinas de exatas para discentes com deficiência visual, intelectual e Transtorno do Espectro Autista (TEA).

## 🚀 Funcionalidades

✅ **Roteamento Híbrido:** Modo **Turbo (Regex) para processamento instantâneo e Modo IA (Gemini 3.5 Flash) para reescrita semântica e audiodescrição.  

♿ **Perfis Customizados:** Adaptação específica para Cegueira, Baixa Visão, TDAH, Autismo e Dislexia.  

🔊 **Math-to-Speech:** Tradução textual de símbolos matemáticos (integrais, somatórios, etc.) e geração automática de áudio MP3 narrado via Google Text-to-Speech (gTTS).  

📄 **Reflow, Ocultamento e Geração de PDF:** Correção de falhas de extração usando a técnica "Liquid Paper", ajustes tipográficos (fontes sem serifa "anti-boxes" como DejaVuSans) e exportação direta do PDF adaptado mantendo o layout original com anotações via PyMuPDF.  

## 🛠 Requisitos  

Antes de rodar a aplicação, certifique-se de ter os seguintes requisitos instalados na sua máquina (ou no servidor do laboratório):  

🟢 **Python** (versão mínima: 3.8+)

📦 **pip** (Gerenciador de pacotes do Python)  

**Dependências Python:**  

-streamlit  

-google-generativeai  

-gtts  

-pymupdf  

-reportlab  

-requests  

## 📌 Como Rodar o Projeto (Configuração de Ambiente)  
Siga o passo a passo abaixo para configurar o ambiente e executar a aplicação:  

### 1. Clonar o repositório
```sh
git clone https://github.com/UFPA-LAMIC/EduAccess-Pro.git
cd EduAccess-Pro
```

### 2. Criar e ativar o Ambiente Virtual  Recomendado Para evitar conflitos de bibliotecas, crie um ambiente virtual Python:

**No Windows:**
```Bash
python -m venv venv
venv\Scripts\activate
```

**No Linux/Mac:**
```Bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as dependências do projeto       Com o ambiente ativado, instale as bibliotecas necessárias

```Bash
pip install streamlit google-generativeai gtts pymupdf reportlab requests
```

### 4. Configurar a Chave da Inteligência Artificial (Google Gemini)
**ATENÇÃO:** Como o processamento cognitivo (TDAH, Autismo e Dislexia) e a transcrição de imagens agora utilizam a API em nuvem do Google Gemini, é estritamente necessário configurar sua chave de acesso localmente.  

Na pasta raiz do projeto, crie uma pasta oculta chamada .streamlit. Dentro dela, crie um arquivo chamado secrets.toml e adicione a sua chave da API do Google com a seguinte estrutura:  

Ini, TOML
GEMINI_API_KEY="sua_chave_aqui"

### 5. Iniciar a Aplicação  

Volte para o terminal onde o ambiente virtual Python está ativado e execute:  

```Bash
streamlit run app.py
```
A aplicação abrirá automaticamente no seu navegador padrão, operando geralmente no endereço http://localhost:8501/.  

### 🤝 Contribuição

Quer contribuir para tornar a educação mais inclusiva? Aqui está como fazer:

Faça um fork do projeto.

Crie uma branch com sua feature:

```Bash
git checkout -b minha-feature
```

Commit suas alterações:

```Bash
git commit -m 'Adicionando nova funcionalidade de acessibilidade'
```

Envie as alterações para o seu fork:

```Bash
git push origin minha-feature
```

Abra um Pull Request para revisão.

### 📜 Licença
Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais detalhes.  

### ❓ Dúvidas  
Se tiver alguma dúvida, dificuldade de instalação ou encontrar algum problema (bug), entre em contato através das seguintes opções:  

📧 E-mail do Laboratório: **lamic@ufpa.br**  

🐞 Reporte um bug abrindo uma issue na aba Issues do GitHub.

Responsáveis pelo projeto:

👨‍🏫 Orientador: Prof. Dr. ALS Castro (agcastro@ufpa.br)

👨‍🎓 Bolsista: Gustavo Tavares Assunção (gustavo.tavares@itec.ufpa.br)

👨‍🎓 Voluntário: Felipe Lima Calvalcante (cavalcante.felipe@itec.ufpa.br)
