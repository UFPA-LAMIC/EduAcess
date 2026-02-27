# EduAccess - Adaptação Multimodal de Materiais com IA

## 📌 Sobre o Projeto

O **EduAccess Pro** faz parte do *Projeto Viva! Universidade 2025: Ampliando a utilização de um ambiente computacional de aprendizagem para pessoas com deficiência*. Ele é uma ferramenta de adaptação de materiais didáticos alimentada por Inteligência Artificial e regras heurísticas (Regex).

Esta aplicação atua como um "motor" de acessibilidade complementar ao **Engenho Academy** (plataforma interativa legada de 2024), automatizando a adequação de PDFs e textos de disciplinas de exatas para discentes com deficiência visual, intelectual e Transtorno do Espectro Autista (TEA).

## 🚀 Funcionalidades

- ✅ **Roteamento Híbrido:** Modo Turbo (Regex) para processamento instantâneo e Modo IA (Modelos Locais) para reescrita semântica.
- ♿ **Perfis Customizados:** Adaptação específica para Cegueira, Baixa Visão, TDAH, Autismo e Dislexia.
- 🔊 **Math-to-Speech:** Tradução textual de símbolos matemáticos (integrais, somatórios, etc.) e geração automática de áudio MP3 narrado via *Google Text-to-Speech* (gTTS).
- 📄 **Reflow e Geração de PDF:** Correção de quebras de linha fantasmas, ajustes de contraste, espaçamento, tipografia (fontes sem serifa "anti-boxes") e exportação direta do PDF adaptado.
- 🔒 **Processamento Local (Privacidade):** Utiliza modelos de linguagem (*LLMs*) rodando localmente na máquina, sem necessidade de enviar dados acadêmicos para nuvens externas.

## 🛠 Requisitos

Antes de rodar a aplicação, certifique-se de ter os seguintes requisitos instalados na sua máquina (ou no servidor do laboratório):

- 🟢 **Python** (versão mínima: 3.8+)
- 📦 **pip** (Gerenciador de pacotes do Python)
- 🦙 **Ollama** (Necessário para rodar a IA localmente. Baixe em: [ollama.com](https://ollama.com/))

**Dependências Python:**
- `streamlit`
- `langchain-ollama`
- `gtts`
- `pypdf`
- `reportlab`
- `requests`

## 📌 Como Rodar o Projeto (Configuração de Ambiente)

Siga o passo a passo abaixo para configurar o ambiente e executar a aplicação:

### 1. Clonar o repositório
```sh
git clone [https://github.com/UFPA-LAMIC/EduAccess-Pro.git](https://github.com/UFPA-LAMIC/EduAccess-Pro.git)
cd EduAccess-Pro
###
### 2. Criar e ativar o Ambiente Virtual (Recomendado)
Para evitar conflitos de bibliotecas, crie um ambiente virtual Python:

**No Windows:**
```bash
python -m venv venv
venv\Scripts\activate

