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
```
### 2. Criar e ativar o Ambiente Virtual (Recomendado)
Para evitar conflitos de bibliotecas, crie um ambiente virtual Python:

**No Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
**No Linux/Mac:**
``` bash
python3 -m venv venv
source venv/bin/activate
```
### 3. Instalar as dependências do projeto
Com o ambiente ativado, instale as bibliotecas necessárias:
``` bash
pip install streamlit langchain-ollama gtts pypdf reportlab requests
```
### 4. Baixar e Preparar a Inteligência Artificial (Llama)
ATENÇÃO: É estritamente necessário baixar o modelo de Inteligência Artificial na sua máquina local para que as funções cognitivas (TDAH, Autismo e Dislexia) funcionem.

Certifique-se de ter instalado o Ollama no seu sistema operacional. Em seguida, abra um terminal (prompt de comando) separado e execute o comando abaixo para baixar e rodar o modelo Llama 3.1 (este download pode demorar dependendo da sua conexão, pois o modelo possui cerca de 4.7 GB):
``` bash
ollama run llama3.1:8b
```
(Deixe este terminal aberto/rodando em segundo plano enquanto utiliza o EduAccess)
### 5. Iniciar a Aplicação
Volte para o terminal onde o ambiente virtual Python está ativado e execute:
``` bash
streamlit run app.py
```
A aplicação abrirá automaticamente no seu navegador padrão, operando geralmente no endereço http://localhost:8501/.
### 🤝 Contribuição
Quer contribuir para tornar a educação mais inclusiva? Aqui está como fazer:
1. Faça um fork do projeto.

2. Crie uma branch com sua feature:
``` bash
git checkout -b minha-feature
```
3. Commit suas alterações:
``` bash
git commit -m 'Adicionando nova funcionalidade de acessibilidade'
```
4. Envie as alterações para o seu fork:
``` bash
git push origin minha-feature
```
5. Abra um Pull Request para revisão.
###📜 Licença
Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais detalhes.
###❓ Dúvidas
Se tiver alguma dúvida, dificuldade de instalação ou encontrar algum problema (bug), entre em contato através das seguintes opções:

-📧 E-mail do Laboratório: lamic@ufpa.br

🐞 Reporte um bug abrindo uma issue na aba Issues do GitHub.

Responsáveis pelo projeto:

-👨‍🏫 Orientador: Prof. Dr. ALS Castro (agcastro@ufpa.br)

-👨‍🎓 Bolsista: Gabriel Silva (silva.gabriel@itec.ufpa.br)
