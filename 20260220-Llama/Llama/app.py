# app.py - EduAccess Pro v34 (Gemini 3.5 Flash Only - Sem PyTorch/pix2tex)
import os
import streamlit as st
import io
import re
import unicodedata
from enum import Enum
from PIL import Image
import requests

# --- INTEGRAÇÃO GOOGLE GEMINI E ÁUDIO ---
try:
    import google.generativeai as genai
except ImportError:
    st.error("ERRO: Instale a biblioteca do Gemini -> pip install google-generativeai")
    st.stop()

try:
    from gtts import gTTS
except ImportError:
    st.error("ERRO: Instale a biblioteca de áudio -> pip install gTTS")
    st.stop()

# Configuração da Chave de API via Streamlit Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("ERRO: Chave da API não encontrada. Crie o arquivo .streamlit/secrets.toml com a sua GEMINI_API_KEY.")
    st.stop()

# --- DEPENDÊNCIAS DE PDF ---
try:
    import fitz  # PyMuPDF
except ImportError:
    st.error("ERRO: Instale PyMuPDF -> pip install pymupdf")
    st.stop()

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    st.error("ERRO: Instale reportlab -> pip install reportlab")
    st.stop()

# ==========================================
# 0. CONFIGURAÇÃO GERAL
# ==========================================
MATH_ITALIC_RANGES = [(0x1D400, 0x1D7FF)]

# ==========================================
# 1. GESTOR DE FONTES
# ==========================================
@st.cache_resource
def setup_fonts():
    font_name = "DejaVuSans.ttf"
    local_path = os.path.abspath(font_name)
    urls = ["https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf"]

    if not os.path.exists(local_path) or os.path.getsize(local_path) < 1000:
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    break
            except Exception:
                continue

    if os.path.exists(local_path):
        try:
            pdfmetrics.registerFont(TTFont('MathFont', local_path))
            return 'MathFont', True
        except Exception:
            pass
    return "Helvetica", False

GLOBAL_FONT, _ = setup_fonts()

# ==========================================
# ENUMS E CONFIG
# ==========================================
class AccessibilityProfile(Enum):
    LOW_VISION = "Baixa Visão"
    BLINDNESS = "Cegueira (Leitor de Tela)"
    ADHD = "TDAH (I.A.)"

st.set_page_config(page_title="EduAccess Pro v34", layout="wide")
if 'adapted_text' not in st.session_state:
    st.session_state.adapted_text = ""
if 'warnings' not in st.session_state:
    st.session_state.warnings = []

# ==========================================
# 2. PROCESSAMENTO E RASTERIZAÇÃO
# ==========================================
def clean_text_artifacts(text):
    t = unicodedata.normalize('NFKC', text) if text else ""
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

def count_letters(text):
    count = 0
    for ch in text:
        cp = ord(ch)
        if ch.isalpha() or any(lo <= cp <= hi for lo, hi in MATH_ITALIC_RANGES):
            count += 1
    return count

def looks_garbled(text):
    if not text:
        return True
    total = len(text)
    suspicious = sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF or (ord(ch) < 9))
    return total > 0 and (suspicious / total) > 0.2

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

def detect_vector_diagrams(page, min_area=2500, min_side=35, min_strokes=5):
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
        # ESCUDO ANTI-TABELAS (70%)
        if r.width > page_width * 0.70:
            continue

        if (r.width >= min_side and r.height >= min_side and
            (r.width * r.height) >= min_area and c["count"] >= min_strokes):
            valid_rects.append(r)

    return valid_rects

def generate_audiodescription(image_bytes):
    """Gera a audiodescrição utilizando a API do Gemini 3.5 Flash"""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return "[AVISO: não foi possível ler esta imagem para gerar a descrição]"

    prompt = (
        "Você é um sistema de audiodescrição técnica. "
        "Descreva este diagrama ou imagem de forma estritamente técnica, clara e objetiva para uma pessoa com deficiência visual. "
        "Se for um circuito elétrico, liste todos os componentes, seus valores exatos conforme escritos, e a topologia das conexões. "
        "Não invente valores que não estão na imagem. "
        "REGRA ESTRITA: Retorne APENAS a audiodescrição. NÃO use NENHUMA saudação, introdução, comentário pessoal "
        "ou nota de encerramento (como 'Olá', 'Aqui está a descrição', 'Como seu assistente', etc.). Vá direto ao conteúdo."
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
    """Transcreve uma fórmula matemática em imagem para código LaTeX usando o Gemini 3.5 Flash."""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return None

    prompt = (
        "Você é um sistema de OCR matemático especializado em transcrever fórmulas para LaTeX. "
        "Transcreva a fórmula matemática presente na imagem para código LaTeX válido, preservando "
        "exatamente os símbolos, subíndices, sobrescritos, frações, variáveis e operadores como aparecem na imagem. "
        "Não resolva, não simplifique, não corrija e não invente símbolos que não estão na imagem. "
        "REGRA ESTRITA: Responda APENAS com o código LaTeX puro — sem cifrão ($), sem blocos de código (```), "
        "sem explicações, sem saudações e sem qualquer texto adicional antes ou depois."
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        latex_code = response.text.strip()

        # Remove possíveis cercas de código ou cifrões que o modelo insista em devolver
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
        page_warnings.append(f"O documento tem {total_pages_doc} páginas; apenas as primeiras {max_pages} foram processadas.")

    needs_visual_desc = profile in (AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS)

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]

        diagram_rects = detect_vector_diagrams(page) if needs_visual_desc else []

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
                if not needs_visual_desc:
                    continue

                is_equation_image = False
                if it["kind"] == "raster_image":
                    img_bbox = it["block"]["bbox"]
                    w = img_bbox[2] - img_bbox[0]
                    h = img_bbox[3] - img_bbox[1]
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio > 3.0:
                        is_equation_image = True

                if is_equation_image:
                    img_bytes = it["block"]["image"]
                    latex_code = generate_latex_ocr(img_bytes)

                    if latex_code and validate_latex(latex_code):
                        processed_content.append(f"\n\n[FÓRMULA (OCR DE IMAGEM)]: $ {latex_code} $\n\n")
                    else:
                        processed_content.append("\n\n[AVISO: FÓRMULA EM IMAGEM ILEGÍVEL]\n\n")
                else:
                    if it["kind"] == "vector_diagram":
                        img_bytes = rasterizar_regiao_pdf(page, it["bbox"], zoom=zoom_diagram)
                    else:
                        img_bytes = it["block"]["image"]

                    desc = generate_audiodescription(img_bytes)
                    processed_content.append(f"\n\n[AUDIODESCRIÇÃO DA IMAGEM]: {desc}\n\n")
                continue

            block = it["block"]
            if id(block) in consumed_ids:
                continue

            text_block = "".join(span["text"] + " " for line in block["lines"] for span in line["spans"])
            bbox = block['bbox']
            altura = bbox[3] - bbox[1]

            letras_normais = count_letters(text_block)
            simbolos_mat = len(re.findall(r'[0-9=\+\-\/\(\)\[\]\{\}\^\_]', text_block))

            is_math = (simbolos_mat > 3) and (letras_normais < 30) and (len(text_block) < 150)
            is_diagram_like = (not is_math) and altura > 100 and len(text_block) < 200

            if is_math:
                cleaned = clean_text_artifacts(text_block)
                if needs_visual_desc and looks_garbled(cleaned):
                    img_bytes = rasterizar_regiao_pdf(page, bbox, zoom=zoom_math)
                    latex_code = generate_latex_ocr(img_bytes)

                    if latex_code and validate_latex(latex_code):
                        processed_content.append(f"\n\n[FÓRMULA LATEX (OCR)]: $ {latex_code} $\n\n")
                    else:
                        processed_content.append(f"\n\n[FÓRMULA - texto original ilegível, revisar manualmente]: {cleaned}\n\n")
                else:
                    processed_content.append(f"\n\n[FÓRMULA]: {cleaned}\n\n")

            elif is_diagram_like:
                if needs_visual_desc:
                    img_bytes = rasterizar_regiao_pdf(page, bbox, zoom=zoom_diagram)
                    desc = generate_audiodescription(img_bytes)
                    processed_content.append(f"\n\n[DIAGRAMA IDENTIFICADO]: {desc}\n\n")
                else:
                    cleaned = clean_text_artifacts(text_block)
                    if cleaned:
                        processed_content.append(cleaned)
            else:
                cleaned = clean_text_artifacts(text_block)
                if cleaned:
                    processed_content.append(cleaned)

        prog_bar.progress((page_num + 1) / total_pages)

    return "\n".join(processed_content), page_warnings

# ==========================================
# 3. PDF E UI
# ==========================================
def create_pdf(text, profile, f_size, line_mult, para_space):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm,
                             topMargin=25 * mm, bottomMargin=25 * mm)
    styles = getSampleStyleSheet()

    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName=GLOBAL_FONT,
        fontSize=f_size,
        leading=f_size * line_mult,
        spaceAfter=para_space
    )

    elems = [Paragraph(f"Material Adaptado - {profile.value}", styles['Heading1']), Spacer(1, 20)]

    for p in text.split('\n\n'):
        if not p.strip():
            continue
        p_safe = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')

        if "[AVISO" in p:
            style_warn = ParagraphStyle('Warn', parent=style_body, textColor='red', leftIndent=20)
            elems.append(Paragraph(f"<b>{p_safe}</b>", style_warn))
        elif "[DIAGRAMA" in p or "[AUDIODESCRIÇÃO" in p or "[FÓRMULA" in p:
            style_ad = ParagraphStyle('AD', parent=style_body, textColor='blue', leftIndent=20)
            elems.append(Paragraph(f"<b>{p_safe}</b>", style_ad))
        else:
            elems.append(Paragraph(p_safe, style_body))

    doc.build(elems)
    buff.seek(0)
    return buff.getvalue()

def main():
    st.sidebar.title("EduAccess Pro v34")
    sel_profile = st.sidebar.selectbox("Necessidade", [p.value for p in AccessibilityProfile])
    profile = AccessibilityProfile(sel_profile)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ajustes de Leitura")
    f_size = st.sidebar.slider("Tamanho Fonte", 10, 30, 14)
    line_spacing = st.sidebar.slider("Entrelinhas", 1.0, 3.0, 1.5)
    para_padding = st.sidebar.slider("Espaço Parágrafos", 0, 50, 15)

    with st.sidebar.expander("Configurações avançadas"):
        max_pages = st.slider("Máximo de páginas a processar", 1, 30, 5)
        zoom_diagram = st.slider("Zoom para diagramas", 1.0, 4.0, 2.0, 0.5)
        zoom_math = st.slider("Zoom para fórmulas", 1.0, 5.0, 3.0, 0.5)

    col1, col2 = st.columns(2)
    with col1:
        up = st.file_uploader("Upload do Material (PDF)", type=['pdf'])
        if st.button("PROCESSAR MATERIAL"):
            if up:
                prog_bar = st.progress(0)
                raw_text, warnings = extract_dla_pipeline(
                    up.read(), profile, prog_bar,
                    max_pages=max_pages,
                    zoom_diagram=zoom_diagram, zoom_math=zoom_math,
                )
                st.session_state.adapted_text = raw_text
                st.session_state.warnings = warnings
                prog_bar.empty()
                st.rerun()
            else:
                st.warning("Selecione um arquivo PDF antes de processar.")

    with col2:
        if st.session_state.warnings:
            for w in st.session_state.warnings:
                st.warning(w)

        if st.session_state.adapted_text:
            st.text_area("Resultado:", st.session_state.adapted_text, height=500)

            # --- BOTÃO DE ÁUDIO NATIVO (TTS) ---
            if st.button("🔊 Ouvir Adaptação"):
                with st.spinner("Sintetizando áudio..."):
                    # Converte o texto da tela para voz (Português do Brasil)
                    tts = gTTS(text=st.session_state.adapted_text, lang='pt', tld='com.br')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    st.audio(audio_fp, format='audio/mp3')

            pdf_bytes = create_pdf(st.session_state.adapted_text, profile, f_size, line_spacing, para_padding)
            st.download_button("Exportar PDF", pdf_bytes, "adaptado.pdf", "application/pdf")

if __name__ == "__main__":
    main()