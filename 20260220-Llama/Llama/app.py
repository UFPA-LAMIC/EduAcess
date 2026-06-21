# app.py - EduAccess Pro v21 (Fix Fonte + IA para Cognitivo + Regex para Visual)
import streamlit as st
import io
import os
import re
import requests
import unicodedata
from enum import Enum

# --- DEPENDÊNCIAS ---
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    st.error("ERRO: Instale gTTS -> pip install gTTS")
    st.stop()

try:
    from pypdf import PdfReader
except ImportError:
    st.error("ERRO: Instale pypdf -> pip install pypdf")
    st.stop()

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
except ImportError:
    st.error("ERRO: Instale reportlab -> pip install reportlab")
    st.stop()

LANGCHAIN_AVAILABLE = False
try:
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    pass

# ==========================================
# 1. GESTOR DE FONTES (RETORNANDO AO MÉTODO QUE FUNCIONA)
# ==========================================
@st.cache_resource
def setup_fonts():
    """
    Usa APENAS o arquivo DejaVuSans.ttf (Regular) para tudo.
    Isso garante que não haja quadrados, pois esse arquivo tem todos os símbolos.
    """
    font_name = "DejaVuSans.ttf"
    local_path = os.path.abspath(font_name)
    
    # Mirrors confiáveis
    urls = [
        "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
        "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
        "https://sourceforge.net/projects/dejavu/files/dejavu/2.37/DejaVuSans.ttf/download"
    ]
    
    # 1. Download
    if not os.path.exists(local_path) or os.path.getsize(local_path) < 1000:
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'} 
                r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(local_path, "wb") as f: f.write(r.content)
                    break 
            except: continue

    # 2. Registro (O "Pulo do Gato" para evitar boxes)
    if os.path.exists(local_path):
        try:
            # Registra a fonte Base
            pdfmetrics.registerFont(TTFont('MathFont', local_path))
            
            # Registra O MESMO ARQUIVO como se fosse Negrito
            # O ReportLab vai "engrossar" a fonte artificialmente ou apenas usar ela,
            # mas garantimos que o glifo (desenho) do símbolo existe.
            pdfmetrics.registerFont(TTFont('MathFont-Bold', local_path)) 
            
            addMapping('MathFont', 0, 0, 'MathFont')
            addMapping('MathFont', 1, 0, 'MathFont-Bold')
            return 'MathFont', True
        except: pass

    # 3. Fallback Sistema Linux
    linux_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for path in linux_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('MathFont', path))
                pdfmetrics.registerFont(TTFont('MathFont-Bold', path))
                addMapping('MathFont', 0, 0, 'MathFont')
                addMapping('MathFont', 1, 0, 'MathFont-Bold')
                return 'MathFont', True
            except: continue
            
    return "Helvetica", False

GLOBAL_FONT, FONT_SUCCESS = setup_fonts()

# ==========================================
# ENUMS
# ==========================================
class AccessibilityProfile(Enum):
    LOW_VISION = "Baixa Visão"
    BLINDNESS = "Cegueira (Leitor de Tela)"
    ADHD = "TDAH (I.A.)"
    AUTISM = "Autismo (I.A.)"
    DYSLEXIA = "Dislexia (I.A.)"

DEFAULT_MODEL = "llama3.1:8b"

st.set_page_config(page_title="EduAccess", layout="wide")

if 'adapted_text' not in st.session_state: st.session_state.adapted_text = ""
if 'audio_bytes' not in st.session_state: st.session_state.audio_bytes = None

# ==========================================
# 2. LIMPEZA E LAYOUT
# ==========================================
def normalize_text(text):
    return unicodedata.normalize('NFC', text) if text else ""

def clean_text_artifacts(text):
    t = unicodedata.normalize('NFC', text) if text else ""
    
    # 0. CORREÇÃO DO "I" FANTASMA E LIGATURAS (O Bug do PyPDF)
    t = t.replace('ı', 'i').replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    
    # 0.5 TRADUÇÃO MATEMÁTICA E GREGA (Adeus Caixas Pretas & Acessibilidade 100%)
    # Transforma símbolos invisíveis para fontes comuns em texto legível
    simbolos_matematicos = {
        'α': ' alfa ', 'β': ' beta ', 'γ': ' gama ', 'θ': ' teta ',
        'ω': ' ômega ', 'π': ' pi ', 'μ': ' micro ', 'Δ': ' delta ',
        'λ': ' lambda ', 'φ': ' fi ', 'ρ': ' rô ', 'τ': ' tau ',
        'σ': ' sigma ', 'Ω': ' ohms ', '°': ' graus ', '±': ' mais ou menos ',
        '×': ' vezes ', '÷': ' dividido por ', '≠': ' diferente de ',
        '≤': ' menor ou igual a ', '≥': ' maior ou igual a ',
        '≈': ' aproximadamente ', '∞': ' infinito ', '√': ' raiz de ',
        '∑': ' somatório de ', '∫': ' integral de ', '∂': ' derivada de ',
        '∇': ' nabla ', '→': ' tende a ', '∈': ' pertence a ',
        '²': ' ao quadrado ', '³': ' ao cubo '
    }
    for sim, nome in simbolos_matematicos.items():
        t = t.replace(sim, nome)
    
    # 1. Corrige a cedilha e falhas do PDF no português
    t = t.replace('¸', ',')
    t = re.sub(r'([cC])\s+,', r'\1,', t)
    t = re.sub(r',\s+([cC])', r',\1', t)
    t = re.sub(r'c\s+ã', 'çã', t)
    t = re.sub(r'c\s+õ', 'çõ', t)
    t = re.sub(r'C\s+ã', 'Çã', t)
    t = re.sub(r'C\s+õ', 'Çõ', t)
    
    # 2. O Pulo do Gato: Tira espaços APENAS se estiverem quebrando letras e acentos
    t = re.sub(r'([a-zA-Z])\s+([~^´`ˆ˜¨])', r'\1\2', t)
    t = re.sub(r'([~^´`ˆ˜¨])\s+([a-zA-Z])', r'\1\2', t)
    
    # 3. Mapeamento Direto Completo
    mapa_acentos = {
        'a~': 'ã', '~a': 'ã', 'o~': 'õ', '~o': 'õ', 'A~': 'Ã', 'O~': 'Õ',
        'a^': 'â', '^a': 'â', 'e^': 'ê', '^e': 'ê', 'o^': 'ô', '^o': 'ô',
        'A^': 'Â', '^A': 'Â', 'E^': 'Ê', '^E': 'Ê', 'O^': 'Ô', '^O': 'Ô',
        'a´': 'á', '´a': 'á', 'e´': 'é', '´e': 'é', 'i´': 'í', '´i': 'í', 
        'o´': 'ó', '´o': 'ó', 'u´': 'ú', '´u': 'ú', 'A´': 'Á', 'E´': 'É',
        'I´': 'Í', 'O´': 'Ó', 'U´': 'Ú',
        'a`': 'à', '`a': 'à', 'A`': 'À', '`A': 'À',
        'c,': 'ç', ',c': 'ç', 'C,': 'Ç', ',C': 'Ç',
        'aˆ': 'â', 'ˆa': 'â', 'eˆ': 'ê', 'ˆe': 'ê', 'oˆ': 'ô', 'ˆo': 'ô',
        'a˜': 'ã', '˜a': 'ã', 'o˜': 'õ', '˜o': 'õ'
    }
    
    for errado, certo in mapa_acentos.items():
        t = t.replace(errado, certo)
        
    # 4. Limpeza de artefatos visuais
    replacements = {
        '\x00': '', '\f': '', '−': '-', '–': '-', '—': '-', 
        '“': '"', '”': '"', '’': "'", '•': '-', '…': '...',
        '▪': '-', '➢': '-', '✓': '-', '●': '-'
    }
    for k, v in replacements.items(): 
        t = t.replace(k, v)
        
    # 5. VAPORIZADOR: Apaga acentos soltos e símbolos invisíveis
    t = re.sub(r'[~^´`ˆ˜¨¸]', '', t)
    
    # 5.5 PURIFICADOR ASCII 
    # Converte o texto para a tabela básica, apagando subscritos (como o 'T' rebaixado)
    # Nós usamos encode e decode e passamos a flag 'ignore' para sumir com os bugs.
    # Como as letras com acento já foram normalizadas na Etapa 3, elas sobrevivem!
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('utf-8')
    
    # 6. Filtro Agressivo (A tag \s aqui garante que os ENTERS fiquem a salvo)
    # Como rodamos o purificador acima, este filtro agora atua como uma barreira extra.
    t = re.sub(r'[^\w\s.,;:!?()\[\]{}"\'/\\@#$%&*+\-=<>|]', '', t)
    
    # 7. CORREÇÃO DA FORMATAÇÃO: Limpa espaços em branco duplos
    t = re.sub(r'[ \t]+', ' ', t)
    
    return t.strip()

def reflow_text(text):
    """Reconstrói parágrafos, preservando títulos e listas na mesma caixa."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 1. Garante que todo título (que começa com #) vire um parágrafo isolado
    text = re.sub(r'\n\s*(#+)', r'\n\n\1', text)
    
    paragraphs = re.split(r'\n\s*\n', text)
    clean_paragraphs = []
    
    for p in paragraphs:
        if not p.strip(): continue
        
        lines = p.split('\n')
        reflowed_lines = []
        current_line = ""
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # 2. O RADAR: Detecta se a linha é um item de lista (-, *, •, 1., a))
            if re.match(r'^([\-\*•]|\d+[\.\)]|[a-zA-Z]\))', line):
                if current_line:
                    reflowed_lines.append(current_line)
                    current_line = ""
                reflowed_lines.append(line)
            else:
                # Se não for lista, junta com a linha anterior
                if current_line:
                    current_line += " " + line
                else:
                    current_line = line
                    
        if current_line:
            reflowed_lines.append(current_line)
            
        # Junta os itens de lista com um Enter simples (\n)
        clean_paragraphs.append("\n".join(reflowed_lines))
        
    return "\n\n".join(clean_paragraphs)

# ==========================================
# 3. MOTORES DE PROCESSAMENTO (ROTEAMENTO AUTOMÁTICO)
# ==========================================

# Motor Rápido (Regex) - Para Visuais
def regex_process(text, profile):
    text = clean_text_artifacts(text)
    text = reflow_text(text)
    
    if profile == AccessibilityProfile.BLINDNESS:
        math_map = {
            '∫': ' integral de ', '∑': ' somatorio de ', '∂': ' derivada parcial ', 
            '∇': ' nabla ', '∀': ' para todo ', '∈': ' pertence a ', '∞': ' infinito ', 
            '√': ' raiz quadrada de ', 'π': ' pi ', '→': ' tende a '
        }
        for k, v in math_map.items(): text = text.replace(k, v)
        text = re.sub(r'\b([a-zA-Z])\(([a-zA-Z0-9])\)', r'\1 de \2', text) 
        text = re.sub(r'\^2', ' ao quadrado', text)
    
    return text

# Motor Inteligente (IA) - Para Cognitivos
def ai_process_smart(text, profile, model_name):
    text = clean_text_artifacts(text)
    text = reflow_text(text)
    
    # Divide por parágrafos duplos
    chunks = text.split('\n\n')
    processed = []
    
    llm = None
    try: 
        # Timeout um pouco maior para garantir que a IA consiga pensar
        llm = ChatOllama(model=model_name, temperature=0.1, timeout=60.0)
    except: return text

    prog_bar = st.progress(0)
    total = len(chunks)
    
    for i, c in enumerate(chunks):
        if len(c) < 20: # Ignora pedaços muito pequenos
            processed.append(c)
            continue
            
        sys_instr = ""
        # PROMPTS PODEROSOS (ESTRUTURADOS)
        if profile == AccessibilityProfile.ADHD:
            sys_instr = "Você é um assistente para TDAH. Simplifique o texto. REGRA CRÍTICA: Use '#' antes de Títulos e '-' para itens de lista. NÃO use asteriscos e NÃO use emojis."
        elif profile == AccessibilityProfile.AUTISM:
            sys_instr = "Você é um assistente para Autismo. Reescreva de forma literal e lógica. REGRA CRÍTICA: Use '#' antes de Títulos e '-' para itens de lista. NÃO use metáforas, asteriscos ou emojis."
        elif profile == AccessibilityProfile.DYSLEXIA:
            sys_instr = "Você é um assistente para Dislexia. Simplifique palavras complexas e estruture visualmente. REGRA CRÍTICA: Use '#' antes de Títulos e '-' para itens de lista. NÃO use asteriscos e NÃO use emojis."
        try:
            # Chama a IA
            resp = (ChatPromptTemplate.from_messages([("system", sys_instr), ("human", "{t}")]) | llm).invoke({"t": c})
            
            # Limpa quebras extras que a IA as vezes coloca
            clean_resp = resp.content.replace('\n', ' ')
            processed.append(clean_resp)
        except:
            # Fallback seguro: devolve o original se a IA falhar
            processed.append(c)
            
        prog_bar.progress((i+1)/total)
    
    prog_bar.empty()
    return "\n\n".join(processed)

# Lógica de Decisão
def smart_router(text, profile_val, model_name):
    profile = AccessibilityProfile(profile_val)
    
    # Se for perfil VISUAL (Cego/Baixa Visão) -> Usa Regex (Rápido)
    if profile in [AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS]:
        return regex_process(text, profile)
    
    # Se for perfil COGNITIVO (TDAH/Autismo/Dislexia) -> Usa IA (Llama)
    else:
        return ai_process_smart(text, profile, model_name)

# ==========================================
# 4. GERAÇÃO PDF
# ==========================================
def create_pdf(text, profile, f_size, line_mult, para_space, align_option):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4, 
        leftMargin=25*mm, rightMargin=25*mm, 
        topMargin=25*mm, bottomMargin=25*mm
    )
    styles = getSampleStyleSheet()
    
    rl_align = TA_LEFT
    if align_option == "Justificado": rl_align = TA_JUSTIFY
    elif align_option == "Centro": rl_align = TA_CENTER
    elif align_option == "Direita": rl_align = TA_RIGHT
    
    style_body = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontName=GLOBAL_FONT, fontSize=f_size,
        leading=f_size * line_mult, spaceAfter=para_space,
        alignment=rl_align, textColor=colors.black,
        splitLongWords=0
    )
    
    style_head = ParagraphStyle(
        'CustomHead', parent=styles['Heading2'],
        fontName=GLOBAL_FONT, fontSize=f_size + 4,
        leading=(f_size + 4) * 1.3, spaceAfter=para_space + 5,
        alignment=TA_LEFT, textColor=colors.black
    )

    elems = []
    elems.append(Paragraph("Material Adaptado", style_head))
    elems.append(Paragraph(f"Perfil: {profile.value}", style_body))
    elems.append(Spacer(1, 20))
    
    paragraphs = text.split('\n\n')
    
    for p in paragraphs:
        if not p.strip(): continue
        
        p_safe = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        p_safe = p_safe.replace('\n', '<br/>')
        p_safe = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', p_safe)
        
        if (len(p) < 100 and p.isupper()) or p.startswith('#'):
            elems.append(Paragraph(p_safe.replace('#', ''), style_head))
        else:
            elems.append(Paragraph(p_safe, style_body))
        
    try:
        doc.build(elems)
        buff.seek(0)
        return buff.getvalue()
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None

# ==========================================
# 5. ÁUDIO
# ==========================================
@st.cache_data(show_spinner=False)
def get_audio_gtts(text):
    if not text.strip(): return None
    try:
        tts = gTTS(text=text, lang='pt', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

# ==========================================
# UI
# ==========================================
def main():
    st.sidebar.title("EduAccess")
    
    if FONT_SUCCESS: st.sidebar.success(f"Fonte Ativa: DejaVu (Anti-Boxes)")
    else: st.sidebar.warning("Usando Fonte Padrão")
    st.sidebar.markdown("---")

    p_names = [p.value for p in AccessibilityProfile]
    sel_profile = st.sidebar.selectbox("Necessidade", p_names)
    profile = AccessibilityProfile(sel_profile)
    
    align_opt = st.sidebar.selectbox("Alinhamento", ["Justificado", "Esquerda", "Centro", "Direita"])
    
    st.sidebar.markdown("### Visual")
    f_size = st.sidebar.slider("Tamanho", 10, 30, 14)
    line_spacing = st.sidebar.slider("Entrelinhas", 1.0, 3.0, 1.5)
    para_padding = st.sidebar.slider("Espaço Parágrafos", 0, 50, 15)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Entrada")
        up = st.file_uploader("PDF/TXT", type=['pdf', 'txt'])
        txt = st.text_area("Texto Manual", height=150)
        
        if st.button("PROCESSAR", type="primary"):
            raw = ""
            if up:
                try: 
                    if up.type == "application/pdf":
                        pdf = PdfReader(io.BytesIO(up.read()))
                        page_limit = 10 
                        raw = "\n\n".join([p.extract_text() for p in pdf.pages[:page_limit] if p.extract_text()])
                    else: raw = up.read().decode('utf-8')
                except: st.error("Erro leitura")
            elif txt: raw = txt
            
            if raw:
                # LÓGICA DE EXECUÇÃO
                if profile in [AccessibilityProfile.ADHD, AccessibilityProfile.AUTISM, AccessibilityProfile.DYSLEXIA]:
                    with st.spinner("IA Analisando (TDAH/Autismo/Dislexia)..."):
                        res = smart_router(raw, sel_profile, DEFAULT_MODEL)
                else:
                    # Cegueira/Baixa Visão é instantâneo (Regex)
                    res = smart_router(raw, sel_profile, DEFAULT_MODEL)
                
                st.session_state.adapted_text = res
                st.session_state.audio_bytes = None
                st.success("Pronto!")

    with col2:
        st.subheader("Saída")
        if st.session_state.adapted_text:
            
            # --- NOVO VISUALIZADOR EDITÁVEL ---
            texto_editado = st.text_area(
                label="📝 Revise e edite o material gerado pela IA:",
                value=st.session_state.adapted_text,
                height=330
            )
            
            # Garantimos que qualquer edição feita pelo professor seja salva
            # e repassada para o Gerador de PDF e Áudio logo abaixo!
            st.session_state.adapted_text = texto_editado
            
            c1, c2 = st.columns(2)
            pdf = create_pdf(st.session_state.adapted_text, profile, f_size, line_spacing, para_padding, align_opt)
            
            if pdf: c1.download_button("📄 Baixar PDF", pdf, "adaptado.pdf", "application/pdf")
            
            if profile == AccessibilityProfile.BLINDNESS:
                if st.button("🔊 Gerar Áudio"):
                    with st.spinner("Gerando MP3..."):
                        mp3 = get_audio_gtts(st.session_state.adapted_text)
                        st.session_state.audio_bytes = mp3
                        st.rerun()
                
                if st.session_state.audio_bytes:
                    st.audio(st.session_state.audio_bytes, format='audio/mp3')
                    st.download_button("⬇️ Baixar MP3", st.session_state.audio_bytes, "audio.mp3", "audio/mpeg")

if __name__ == "__main__":
    main()
