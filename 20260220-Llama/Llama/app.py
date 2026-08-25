<<<<<<< Updated upstream
# app.py - EduAccess Pro v21 (Fix Fonte + IA para Cognitivo + Regex para Visual)
=======
# app.py - EduAccess Pro v40 (Gemini 3.1 Flash Lite - UX Visual para TDAH)
import os
import time
>>>>>>> Stashed changes
import streamlit as st
import io
import os
import re
<<<<<<< Updated upstream
import requests
=======
import math
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
>>>>>>> Stashed changes
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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
<<<<<<< Updated upstream
    from reportlab.lib.fonts import addMapping
=======
    from reportlab.lib.enums import TA_LEFT 
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
DEFAULT_MODEL = "llama3.1:8b"

st.set_page_config(page_title="EduAccess", layout="wide")

if 'adapted_text' not in st.session_state: st.session_state.adapted_text = ""
if 'audio_bytes' not in st.session_state: st.session_state.audio_bytes = None

# ==========================================
# 2. LIMPEZA E LAYOUT
# ==========================================
def normalize_text(text):
    return unicodedata.normalize('NFC', text) if text else ""
=======
st.set_page_config(page_title="EduAccess Pro v40", layout="wide")
if 'adapted_text' not in st.session_state:
    st.session_state.adapted_text = ""
if 'warnings' not in st.session_state:
    st.session_state.warnings = []

# ==========================================
# FUNÇÕES DE SANITIZAÇÃO E TTS
# ==========================================
def sanitizar_para_tts(texto):
    if not texto: return ""
    t = re.sub(r'[\$]', '', texto)
    t = re.sub(r'_([a-zA-Z0-9])', r' \1', t)
    return t

def translate_latex_to_speech(latex_code):
    prompt = (
        f"Transforme este código LaTeX em texto corrido para um leitor de tela em português do Brasil. "
        f"Escreva por extenso como a fórmula deve ser lida em voz alta (ex: '\\frac{{x}}{{y}}' vira 'x sobre y', "
        f"'\\frac{{d|R|}}{{dt}}' vira 'derivada do módulo do vetor R em relação a t').\n\n"
        f"Código: {latex_code}\n\n"
        f"REGRA ESTRITA: Responda APENAS com a leitura em português, sem formatação extra ou explicações."
    )
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return "Erro na conversão fonética da fórmula."

def translate_instructional_text(text):
    if not re.search(r'[a-zA-Z]', text) or len(text) < 5: return text
    
    # Delay obrigatório para não estourar o limite da API no loop de texto
    time.sleep(3.5) 
    
    prompt = (
        f"Verifique o seguinte texto técnico. Se contiver instruções em inglês (ex: 'Sketch', 'Find', 'Ans.'), "
        f"TRADUZA OBRIGATORIAMENTE para o português do Brasil. "
        f"Se já estiver em português ou for apenas variáveis isoladas, retorne EXATAMENTE o texto original.\n"
        f"Texto: {text}"
    )
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return text

# ==========================================
# 2. PROCESSAMENTO E RASTERIZAÇÃO
# ==========================================
def apply_bionic_reading(text):
    if not text:
        return ""
        
    def bionic_word(match):
        word = match.group(0)
        if len(word) == 1:
            return f"<b>{word}</b>"
            
        mid = math.ceil(len(word) / 2)
        return f"<b>{word[:mid]}</b>{word[mid:]}"
        
    parts = re.split(r'(<[^>]+>)', text)
    for i in range(len(parts)):
        if not parts[i].startswith('<'):
            parts[i] = re.sub(r'[a-zA-ZáéíóúâêôãõçàÀÁÉÍÓÚÂÊÔÃÕÇ]+', bionic_word, parts[i])
            
    return "".join(parts)

def chunk_and_bionic(text):
    if not text:
        return ""
    
    if len(text) > 120 and "." in text:
        sentences = [s.strip() for s in text.split(". ") if s.strip()]
        if len(sentences) > 1:
            chunked_text = "<br/>".join([f"• {apply_bionic_reading(s)}." for s in sentences])
            return chunked_text
            
    return apply_bionic_reading(text)

def draw_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(HexColor("#fdf6e3"))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()

def build_accessible_pdf(elements_data):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
        topMargin=25*mm, bottomMargin=25*mm
    )
    
    styles = getSampleStyleSheet()
    
    tdah_style = ParagraphStyle(
        'TDAH_Style', parent=styles['Normal'], fontName='Helvetica', 
        fontSize=14, leading=21, spaceAfter=15, textColor=HexColor("#2c2c2c"), alignment=TA_LEFT
    )
    
    tdah_desc_style = ParagraphStyle(
        'TDAH_Desc', parent=tdah_style, fontSize=12, textColor=HexColor("#4a4a4a")
    )

    h1_style = ParagraphStyle(
        'H1_Style', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=16, spaceAfter=12, textColor=HexColor("#1a1a1a")
    )
    
    h2_style = ParagraphStyle(
        'H2_Style', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=14, spaceAfter=8, textColor=HexColor("#333333")
    )
    
    story = []
    
    for elem in elements_data:
        if elem["type"] == "lixo_visual":
            continue
            
        content = elem.get("content", "")
            
        if elem["type"] == "texto_normal":
            if not content: continue

            if any(content.startswith(k) for k in ["Objetivo", "Prática", "Pergunta", "DESTAQUE"]):
                story.append(Spacer(1, 5*mm))
                story.append(Paragraph(f"<b>{content}</b>", h1_style))
                continue
            elif content.startswith("Passo") or content.startswith("Discussão"):
                story.append(Paragraph(f"<b>{content}</b>", h2_style))
                continue

            if ("Figura 1" in content and "Figura 2" in content and "Figura 3" in content) or ("Medição" in content and ("Tensão" in content or "Completo" in content)):
                table_data = [
                    ["Medição", "Fig. 1 (Completo)", "Fig. 2 (C. Aberto)", "Fig. 3 (Thévenin)"],
                    ["Tensão (V)", "v_L = ", "v_OC = ", "v_L = "],
                    ["Corr. / Resist.", "i_L = ", "R_TH = ", "i_L = "]
                ]
                t = Table(table_data, colWidths=[35*mm, 42*mm, 43*mm, 40*mm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), HexColor("#e0e0e0")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 10),
                    ('BACKGROUND', (0,1), (-1,-1), HexColor("#fdf6e3")),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('FONTSIZE', (0,0), (-1,-1), 12),
                ]))
                story.append(Spacer(1, 8*mm))
                story.append(t)
                story.append(Spacer(1, 8*mm))
                continue

            bionic_text = chunk_and_bionic(content)
            story.append(Paragraph(bionic_text, tdah_style))
            
        elif elem["type"] == "audiodescricao":
            if not content: continue
            
            parts = content.split("TAGS VISUAIS:")
            desc_text = parts[0].strip()
            tags_text = parts[1].strip() if len(parts) > 1 else ""

            bionic_text = apply_bionic_reading(desc_text)
            story.append(Paragraph(f"<i>{bionic_text}</i>", tdah_desc_style))
            
            if "img_bytes" in elem and elem["img_bytes"]:
                try:
                    img_stream = io.BytesIO(elem["img_bytes"])
                    img = RLImage(img_stream)
                    img._restrictSize(160 * mm, 200 * mm) 
                    img.hAlign = 'CENTER'
                    story.append(Spacer(1, 3*mm))
                    story.append(img)
                    
                    if tags_text and tags_text.lower() != "nenhuma tag":
                        story.append(Spacer(1, 2*mm))
                        story.append(Paragraph(f"<b>Apoio Visual:</b> {tags_text}", tdah_desc_style))
                        
                except Exception as e:
                    story.append(Paragraph(f"[AVISO: Falha ao renderizar imagem: {e}]", tdah_style))

        # NOVO BLOCO: Renderiza imagem limpa para fórmulas no perfil TDAH
        elif elem["type"] == "formula_visual":
            if "img_bytes" in elem and elem["img_bytes"]:
                try:
                    img_stream = io.BytesIO(elem["img_bytes"])
                    img = RLImage(img_stream)
                    img._restrictSize(120 * mm, 40 * mm) 
                    img.hAlign = 'LEFT'
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph("[AVISO: Falha ao renderizar fórmula visual]", tdah_style))

        elif elem["type"] in ["formula", "aviso"]:
            if not content: continue
            story.append(Paragraph(content, tdah_style))
            
        story.append(Spacer(1, 5*mm))

    doc.build(story, onFirstPage=draw_background, onLaterPages=draw_background)
    return buff.getvalue()
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
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
=======
def count_letters(text):
    count = 0
    for ch in text:
        cp = ord(ch)
        if ch.isalpha() or any(lo <= cp <= hi for lo, hi in MATH_ITALIC_RANGES):
            count += 1
    return count

def validate_latex(code):
    if not code or not (2 <= len(code) <= 400):
        return False
    pairs = {'{': '}', '(': ')', '[': ']'}
    stack = []
    for ch in code:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                return False
    if stack:
        return False
    suspicious_tokens = ['\\boldmath', '\\proyte', '\\mit}', '\\longrightarrow\\longrightarrow']
    if any(tok in code for tok in suspicious_tokens):
        return False
    if code.count('\\qquad') > 5:
        return False
    return True

def rasterizar_regiao_pdf(page, bbox, zoom=2.0):
    rect = fitz.Rect(bbox)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
    return pix.tobytes("png")

def _rects_overlap(a, b, margin=2):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 + margin < bx0 or bx1 + margin < ax0 or ay1 + margin < by0 or by1 + margin < ay0)

def detect_vector_diagrams(page, min_area=4000, min_side=50, min_strokes=5):
    try:
        drawings = page.get_drawings()
    except Exception:
        return []
    if not drawings:
        return []

    page_width = page.rect.width
    clusters = []
    for d in drawings:
        r = d.get("rect")
        if not r or r.width <= 0 or r.height <= 0:
            continue
        fr = fitz.Rect(r)
        added = False
        for c in clusters:
            if _rects_overlap(tuple(c["rect"]), tuple(fr), margin=15):
                c["rect"] |= fr
                c["count"] += 1
                added = True
                break
        if not added:
            clusters.append({"rect": fr, "count": 1})

    changed = True
    guard = 0
    while changed and len(clusters) > 1 and guard < 20:
        changed = False
        guard += 1
        merged = []
        used = [False] * len(clusters)
        for i in range(len(clusters)):
            if used[i]:
                continue
            base_cluster = clusters[i]
            for j in range(i + 1, len(clusters)):
                if used[j]:
                    continue
                if _rects_overlap(tuple(base_cluster["rect"]), tuple(clusters[j]["rect"]), margin=15):
                    base_cluster["rect"] |= clusters[j]["rect"]
                    base_cluster["count"] += clusters[j]["count"]
                    used[j] = True
                    changed = True
            used[i] = True
            merged.append(base_cluster)
        clusters = merged

    valid_rects = []
    for c in clusters:
        r = c["rect"]
        if r.width > page_width * 0.70:
            continue
        if (r.width >= min_side and r.height >= min_side and
            (r.width * r.height) >= min_area and c["count"] >= min_strokes):
            valid_rects.append(r)
    return valid_rects

def generate_audiodescription(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return "[AVISO: não foi possível ler esta imagem para gerar a descrição]"

    prompt = (
        """Você é um especialista em audiodescrição técnica para pessoas com deficiência visual. Sua tarefa é descrever o diagrama, gráfico ou imagem de forma estritamente técnica, clara e estruturada.

DIRETRIZES DE DESCRIÇÃO:
Visão Geral: Comece sempre com um resumo macro do que a imagem representa e sua finalidade aparente antes de detalhar as partes.
Detalhamento Lógico e Estrutural: Descreva a organização seguindo um sentido de leitura claro. Liste os elementos, componentes, rótulos e seus valores exatos.
Estados, Formas e Representações Visuais: Relate explicitamente o estado físico, visual ou estrutural dos elementos.
Leitura de Tela (Acessibilidade): Escreva siglas, variáveis e fórmulas de forma estruturada.
Fidelidade Absoluta: Não deduza, não resolva e não invente valores.

REGRA ESTRITA: Retorne APENAS o texto contínuo da audiodescrição. Sem formatação Markdown. Vá direto ao primeiro caractere do conteúdo.
Além da descrição, adicione obrigatoriamente no final uma linha começando com "TAGS VISUAIS:" listando os pontos críticos (ex: curto-circuito, chaves abertas). Se não houver, coloque "TAGS VISUAIS: Nenhuma tag"."""
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        desc = response.text.strip()
        if not desc:
            return "[AVISO: O modelo retornou uma descrição vazia.]"
        return desc
    except Exception as e:
        return f"[AVISO: Falha na API do Gemini ({e}) — revise manualmente]"

def generate_audiodescription_nd(image_bytes, contexto_anterior=""):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return "[AVISO: não foi possível ler esta imagem para gerar a descrição]"

    prompt_contexto = ""
    if contexto_anterior:
        prompt_contexto = f"\nO usuário já conhece a base do circuito/imagem anterior: '{contexto_anterior}'. Nesse caso, NÃO liste os componentes básicos novamente. Foque APENAS na alteração, isolamento, ou nova marcação.\n"

    prompt = (
        f"""Você é um especialista em acessibilidade cognitiva. Sua tarefa é descrever este diagrama técnico para uma pessoa neurodivergente (foco em TDAH).
{prompt_contexto}
DIRETRIZES DA DESCRIÇÃO COGNITIVA:
1. O Conceito Primeiro (Bottom-Line Up Front): Diga diretamente o que o diagrama representa.
2. Fluxo em Lista (Antidensidade): Descreva o funcionamento OBRIGATORIAMENTE como uma lista numerada passo a passo. 
3. Formatação ReportLab: Você DEVE usar tags HTML para estruturar o texto. Use <br/> para quebra de linha entre os passos. Use <b> para destacar componentes. Para subscritos, use a tag <sub> (Ex: v<sub>L</sub>, i<sub>L</sub>, R<sub>TH</sub>).
4. Topologia > Geometria (Orientação): É ESTRITAMENTE PROIBIDO usar termos espaciais ou visuais (como "à direita", "no centro", "embaixo"). Use APENAS referências topológicas.
5. Destaques Semânticos: Explique o *significado* de setas ou retângulos pontilhados.
6. Filtro de Ruído Absoluto: Ignore elementos puramente decorativos. Se for lixo visual, retorne EXATAMENTE "LIXO_VISUAL".

REGRA ESTRITA: Retorne APENAS a descrição. Sem markdown extra. 
Finalize obrigatoriamente com a linha "TAGS VISUAIS:" listando os conceitos críticos."""
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        desc = response.text.strip()
        if not desc:
            return "[AVISO: O modelo retornou uma descrição vazia.]"
        return desc
    except Exception as e:
        return f"[AVISO: Falha na API do Gemini ({e}) — revise manualmente]"

def generate_latex_ocr(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return None

    prompt = (
        """Você é um sistema automatizado de OCR matemático de altíssima precisão. Sua única função é transcrever fórmulas matemáticas presentes em imagens para código LaTeX válido.

DIRETRIZES DE TRANSCRIÇÃO:
Preservação Absoluta: Mantenha exatamente os símbolos e operadores.
Filtro de Ruído: Ignore COMPLETAMENTE textos instrucionais marginais. Foque estritamente na matemática. Se houver texto essencial DENTRO da equação, traduza-o para o português.
Matrizes e Estruturas Complexas: Respeite dimensões usando ambientes corretos.
Texto e Espaçamento: Encapsule texto no comando \\text{}.
Sem Alterações Analíticas: Não resolva as contas.

REGRA ESTRITA: Responda EXCLUSIVAMENTE com o código puro. Sem marcações Markdown."""
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        latex_code = response.text.strip()
        latex_code = re.sub(r'^```[a-zA-Z]*\n?', '', latex_code)
        latex_code = re.sub(r'```$', '', latex_code).strip()
        latex_code = latex_code.strip('$').strip()
        return latex_code if latex_code else None
    except Exception:
        return None

def extract_dla_pipeline(pdf_bytes, profile, prog_bar, max_pages=5, zoom_diagram=2.0, zoom_math=3.0):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    processed_content = []
    page_warnings = []

    total_pages_doc = len(doc)
    total_pages = min(total_pages_doc, max_pages)
    if total_pages_doc > max_pages:
        page_warnings.append(f"O documento tem {total_pages_doc} páginas; apenas as {max_pages} foram processadas.")

    needs_api = True 
    is_tdah = profile == AccessibilityProfile.ADHD
    ultimo_contexto_diagrama = "" 

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        diagram_rects = detect_vector_diagrams(page) if True else []

        items = []
        for b in blocks:
            kind = "raster_image" if b["type"] == 1 else "text"
            items.append({"kind": kind, "bbox": b["bbox"], "block": b})
        for r in diagram_rects:
            items.append({"kind": "vector_diagram", "bbox": tuple(r)})
        items.sort(key=lambda it: (round(it["bbox"][1], 1), round(it["bbox"][0], 1)))

        consumed_ids = set()
        for it in items:
            if it["kind"] == "vector_diagram":
                for other in items:
                    if other["kind"] == "text" and _rects_overlap(it["bbox"], other["bbox"]):
                        consumed_ids.add(id(other["block"]))

        for it in items:
            if it["kind"] in ("vector_diagram", "raster_image"):
                bbox_img = it["bbox"] if it["kind"] == "vector_diagram" else it["block"]["bbox"]
                if it["kind"] == "vector_diagram":
                    img_bytes = rasterizar_regiao_pdf(page, it["bbox"], zoom=zoom_diagram)
                else:
                    img_bytes = it["block"]["image"]

                is_equation_image = False
                if it["kind"] == "raster_image":
                    img_bbox = it["block"]["bbox"]
                    w = img_bbox[2] - img_bbox[0]
                    h = img_bbox[3] - img_bbox[1]
                    if w >= 25 and h >= 25:
                        aspect_ratio = w / h if h > 0 else 0
                        if aspect_ratio > 3.0:
                            is_equation_image = True

                if is_equation_image:
                    if profile in (AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS):
                        st.toast(f"Página {page_num + 1}: Analisando equação...") 
                        time.sleep(3.5)
                        latex_code = generate_latex_ocr(img_bytes)
                        if latex_code and validate_latex(latex_code):
                            tts_text = translate_latex_to_speech(latex_code) if profile == AccessibilityProfile.BLINDNESS else ""
                            processed_content.append({
                                "page_num": page_num, "bbox": bbox_img, "type": "formula", 
                                "content": f"[FÓRMULA LATEX]: $ {latex_code} $", 
                                "tts_content": f"Fórmula: {tts_text}",
                                "img_bytes": img_bytes
                            })
                        else:
                            processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "aviso", "content": "[AVISO: FÓRMULA ILEGÍVEL]", "tts_content": "Aviso: Fórmula ilegível.", "img_bytes": img_bytes})
                    elif profile == AccessibilityProfile.ADHD:
                        processed_content.append({
                            "page_num": page_num, "bbox": bbox_img, "type": "formula_visual", 
                            "content": "", 
                            "tts_content": "Fórmula matemática.",
                            "img_bytes": img_bytes
                        })
                else:
                    if is_tdah:
                        st.toast(f"Página {page_num + 1}: Analisando diagrama cognitivo...")
                        time.sleep(3.5)
                        desc_cognitiva = generate_audiodescription_nd(img_bytes, ultimo_contexto_diagrama)
                        
                        if "LIXO_VISUAL" not in desc_cognitiva:
                            desc_cognitiva = sanitizar_para_tts(desc_cognitiva)
                            ultimo_contexto_diagrama = desc_cognitiva.split("TAGS VISUAIS:")[0].strip()
                            processed_content.append({
                                "page_num": page_num, "bbox": bbox_img, "type": "audiodescricao",
                                "content": f"[APOIO CONCEITUAL]:<br/>{desc_cognitiva}", 
                                "tts_content": f"Apoio conceitual: {desc_cognitiva}",
                                "img_bytes": img_bytes
                            })
                    elif profile in (AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS):
                        st.toast(f"Página {page_num + 1}: Gerando audiodescrição técnica...")
                        time.sleep(3.5)
                        desc = generate_audiodescription(img_bytes)
                        processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "audiodescricao", "content": f"[AUDIODESCRIÇÃO]: {desc}", "tts_content": f"Audiodescrição: {desc}", "img_bytes": img_bytes})
                continue

            block = it["block"]
            text_block = "".join(span["text"] + " " for line in block["lines"] for span in line["spans"])
            bbox_txt = block['bbox']
            
            if re.search(r'W{2,}', text_block) or "M WW" in text_block:
                processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "lixo_visual", "content": ""})
                continue 
            
            if id(block) in consumed_ids:
                continue

            altura = bbox_txt[3] - bbox_txt[1]
            letras_normais = count_letters(text_block)
            operadores_fortes = len(re.findall(r'[=\+\*\^\[\]\{\}<>]', text_block))
            simbolos_mat = len(re.findall(r'[0-9=\+\-\/\(\)\[\]\{\}\^]', text_block))
            parece_data_hora = bool(re.search(r'\d{2}/\d{2}|\d{2}:\d{2}', text_block))
            
            # Lógica mais inteligente para detectar matemática misturada com texto
            is_math = (simbolos_mat > 3 or operadores_fortes > 0) and not parece_data_hora
            
            # Se for um texto gigante (como um parágrafo inteiro), não é fórmula isolada
            if is_math and len(text_block) > 250 and operadores_fortes < 2:
                is_math = False

            if is_math:
                cleaned = clean_text_artifacts(text_block)
                if profile in (AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS):
                    st.toast(f"Página {page_num + 1}: Extraindo matemática com IA...")
                    time.sleep(3.5)
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_math)
                    latex_code = generate_latex_ocr(img_bytes)
                    if latex_code and validate_latex(latex_code):
                        tts_text = translate_latex_to_speech(latex_code) if profile == AccessibilityProfile.BLINDNESS else ""
                        processed_content.append({
                            "page_num": page_num, "bbox": bbox_txt, "type": "formula", 
                            "content": f"[FÓRMULA LATEX]: $ {latex_code} $",
                            "tts_content": f"Fórmula: {tts_text}"
                        })
                    else:
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "aviso", "content": f"[FÓRMULA ILEGÍVEL]: {cleaned}", "tts_content": f"Fórmula ilegível: {cleaned}"})
                elif profile == AccessibilityProfile.ADHD:
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_math)
                    processed_content.append({
                        "page_num": page_num, "bbox": bbox_txt, "type": "formula_visual", 
                        "content": "", 
                        "tts_content": "Fórmula matemática.",
                        "img_bytes": img_bytes
                    })

            elif is_diagram_like:
                cleaned = clean_text_artifacts(text_block)
                if cleaned:
                    cleaned = translate_instructional_text(cleaned)
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "texto_normal", "content": cleaned, "tts_content": cleaned})
            else:
                cleaned = clean_text_artifacts(text_block)
                if cleaned:
                    cleaned = translate_instructional_text(cleaned)
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "texto_normal", "content": cleaned, "tts_content": cleaned})

        prog_bar.progress((page_num + 1) / total_pages)

    return processed_content, page_warnings

# ==========================================
# 3. PDF E UI
# ==========================================
def inject_annotations_into_pdf(pdf_bytes, elements_data):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for elem in elements_data:
        if elem["type"] == "texto_normal":
            continue
            
        page = doc.load_page(elem["page_num"])
        rect = fitz.Rect(elem["bbox"])
        
        if elem["type"] == "lixo_visual":
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            continue
        
        annot = page.add_text_annot(rect.top_left, elem["content"])
        
        if elem["type"] == "audiodescricao":
            annot.set_info(title="Áudio Descrição (IA)")
            annot.set_colors(stroke=(0.0, 0.5, 1.0)) 
        elif elem["type"] == "formula":
            annot.set_info(title="Fórmula Adaptada")
            annot.set_colors(stroke=(1.0, 0.0, 0.0)) 
        elif elem["type"] == "aviso":
            annot.set_info(title="Aviso de Acessibilidade")
            annot.set_colors(stroke=(1.0, 0.5, 0.0)) 
>>>>>>> Stashed changes
            
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
<<<<<<< Updated upstream
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
=======
    doc.save(buff)
    return buff.getvalue()

def main():
    st.sidebar.title("EduAccess Pro v40")
    sel_profile = st.sidebar.selectbox("Necessidade", [p.value for p in AccessibilityProfile])
    profile = AccessibilityProfile(sel_profile)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ajustes de Leitura")
    f_size = st.sidebar.slider("Tamanho Fonte (Pré-visualização)", 10, 30, 14) 

    with st.sidebar.expander("Configurações avançadas"):
        max_pages = st.slider("Máximo de páginas a processar", 1, 30, 15)
        zoom_diagram = st.slider("Zoom para diagramas", 1.0, 4.0, 2.0, 0.5)
        zoom_math = st.slider("Zoom para fórmulas", 1.0, 5.0, 3.0, 0.5)
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
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
=======
                prog_bar = st.progress(0)
                original_pdf_bytes = up.read() 
                
                with st.spinner("Extraindo arquitetura do PDF com IA..."):
                    raw_data, warnings = extract_dla_pipeline(
                        original_pdf_bytes, profile, prog_bar,
                        max_pages=max_pages,
                        zoom_diagram=zoom_diagram, zoom_math=zoom_math,
                    )
                st.session_state.adapted_data = raw_data
                st.session_state.warnings = warnings
                st.session_state.original_pdf_bytes = original_pdf_bytes 
                
                prog_bar.empty()
                st.rerun()
            else:
                st.warning("Selecione um arquivo PDF antes de processar.")

    with col2:
        if "warnings" in st.session_state and st.session_state.warnings:
            for w in st.session_state.warnings:
                st.warning(w)

        if "adapted_data" in st.session_state and st.session_state.adapted_data:
            texto_para_tela = "\n\n".join([item["content"] for item in st.session_state.adapted_data])
            texto_para_audio = "\n\n".join([item.get("tts_content", item["content"]) for item in st.session_state.adapted_data])
            
            st.text_area("Pré-visualização do Conteúdo:", texto_para_tela, height=500)

            if st.button("🔊 Ouvir Adaptação"):
                with st.spinner("Sintetizando áudio fonético..."):
                    tts = gTTS(text=texto_para_audio, lang='pt', tld='com.br')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    st.audio(audio_fp, format='audio/mp3')

            if "original_pdf_bytes" in st.session_state:
                if profile == AccessibilityProfile.ADHD:
                    pdf_bytes_final = build_accessible_pdf(st.session_state.adapted_data)
                    st.download_button("Exportar PDF Acessível (TDAH)", pdf_bytes_final, "adaptado_TDAH.pdf", "application/pdf")
                else:
                    pdf_bytes_final = inject_annotations_into_pdf(st.session_state.original_pdf_bytes, st.session_state.adapted_data)
                    st.download_button("Exportar PDF Acessível", pdf_bytes_final, "adaptado.pdf", "application/pdf")
>>>>>>> Stashed changes

if __name__ == "__main__":
    main()
