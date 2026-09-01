# app.py - EduAccess Pro Unificado (v36 + v34 Merge)
import os
import time
import streamlit as st
import io
import re
import math
from functools import partial
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT 
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
    DYSLEXIA = "Dislexia (I.A.)"
    AUTISM = "Autismo (I.A.)"

st.set_page_config(page_title="EduAccess Pro (Merge v36+v34)", layout="wide")
if 'adapted_text' not in st.session_state:
    st.session_state.adapted_text = ""
if 'warnings' not in st.session_state:
    st.session_state.warnings = []

# ==========================================
# FUNÇÃO: SANITIZAÇÃO PARA TTS (Da v36)
# ==========================================
def sanitizar_para_tts(texto):
    """Remove caracteres matemáticos que quebram o leitor de tela."""
    if not texto: return ""
    t = re.sub(r'[\$]', '', texto)
    t = re.sub(r'_([a-zA-Z0-9])', r' \1', t) # Transforma v_L em v L
    return t

# ==========================================
# PDF BUILDER: NEURODIVERGÊNCIA (Da v36)
# ==========================================
def apply_bionic_reading(text):
    if not text: return ""
    def bionic_word(match):
        word = match.group(0)
        if len(word) == 1: return f"<b>{word}</b>"
        mid = math.ceil(len(word) / 2)
        return f"<b>{word[:mid]}</b>{word[mid:]}"
    return re.sub(r'[a-zA-ZáéíóúâêôãõçàÀÁÉÍÓÚÂÊÔÃÕÇ]+', bionic_word, text)

def chunk_and_bionic(text):
    if not text: return ""
    if len(text) > 120 and "." in text:
        sentences = [s.strip() for s in text.split(". ") if s.strip()]
        if len(sentences) > 1:
            chunked_text = "<br/>".join([f"• {apply_bionic_reading(s)}." for s in sentences])
            return chunked_text
    return apply_bionic_reading(text)

def draw_background(canvas, doc, profile):
    canvas.saveState()
    if profile == AccessibilityProfile.DYSLEXIA:
        bg_color = HexColor("#F5F5DC") # Creme suave
    elif profile == AccessibilityProfile.AUTISM:
        bg_color = HexColor("#F0F4F8") # Azul pastel calmante
    else:
        bg_color = HexColor("#fdf6e3") # Padrão original
    canvas.setFillColor(bg_color)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()

def build_accessible_pdf(elements_data, profile):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
        topMargin=25*mm, bottomMargin=25*mm
    )
    styles = getSampleStyleSheet()
    line_spacing = 28 if profile == AccessibilityProfile.DYSLEXIA else 21
    text_color = HexColor("#333333")
    
    base_style = ParagraphStyle(
        'Base_Style', parent=styles['Normal'], fontName='Helvetica', 
        fontSize=14, leading=line_spacing, spaceAfter=15, textColor=text_color, alignment=TA_LEFT
    )
    desc_style = ParagraphStyle('Desc_Style', parent=base_style, fontSize=12, textColor=HexColor("#4a4a4a"))
    h1_style = ParagraphStyle('H1_Style', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, spaceAfter=12, textColor=HexColor("#1a1a1a"))
    h2_style = ParagraphStyle('H2_Style', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, textColor=HexColor("#333333"))
    
    story = []
    
    for elem in elements_data:
        if elem["type"] == "lixo_visual": continue
            
        content = elem.get("content", "")
            
        if elem["type"] == "texto_normal":
            if not content: continue
            if any(content.startswith(k) for k in ["Objetivo", "Prática", "Pergunta", "DESTAQUE"]):
                story.append(Spacer(1, 5*mm))
                story.append(Paragraph(f"<b>{content}</b>", h1_style))
                continue
            elif content.startswith("Passo") or content.startswith("Discussão"):
                if profile == AccessibilityProfile.AUTISM and content.startswith("Passo"):
                    content = f"[  ] {content}"
                story.append(Paragraph(f"<b>{content}</b>", h2_style))
                continue

            if "v L = v OC = v L =" in content or "Figura 1 Figura 2 Figura 3" in content:
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

            if profile == AccessibilityProfile.ADHD:
                final_text = chunk_and_bionic(content)
            else:
                final_text = content
                
            story.append(Paragraph(final_text, base_style))
            
        elif elem["type"] == "audiodescricao":
            if not content: continue
            
            parts = content.split("TAGS VISUAIS:")
            desc_text = parts[0].strip()
            tags_text = parts[1].strip() if len(parts) > 1 else ""

            if profile == AccessibilityProfile.ADHD:
                final_desc = apply_bionic_reading(desc_text)
            else:
                final_desc = desc_text
                
            story.append(Paragraph(f"<i>{final_desc}</i>", desc_style))
            
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
                        story.append(Paragraph(f"<b>Apoio Visual:</b> {tags_text}", desc_style))
                        
                except Exception as e:
                    story.append(Paragraph(f"[AVISO: Falha ao renderizar imagem: {e}]", base_style))

        elif elem["type"] in ["formula", "aviso"]:
            if not content: continue
            story.append(Paragraph(content, base_style))
            
        story.append(Spacer(1, 5*mm))

    bg_func = partial(draw_background, profile=profile)
    doc.build(story, onFirstPage=bg_func, onLaterPages=bg_func)
    return buff.getvalue()

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
    if not text: return True
    total = len(text)
    suspicious = sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF or (ord(ch) < 9))
    return total > 0 and (suspicious / total) > 0.2

def validate_latex(code):
    if not code or not (2 <= len(code) <= 400): return False
    pairs = {'{': '}', '(': ')', '[': ']'}
    stack = []
    for ch in code:
        if ch in pairs: stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch: return False
    if stack: return False
    suspicious_tokens = ['\\boldmath', '\\proyte', '\\mit}', '\\longrightarrow\\longrightarrow']
    if any(tok in code for tok in suspicious_tokens): return False
    if code.count('\\qquad') > 5: return False
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
        if not r or r.width <= 0 or r.height <= 0: continue
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
            if used[i]: continue
            base_cluster = clusters[i]
            for j in range(i + 1, len(clusters)):
                if used[j]: continue
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
        # ESCUDO ANTI-TABELAS (V34)
        if r.width > page_width * 0.70:
            continue
        if (r.width >= min_side and r.height >= min_side and (r.width * r.height) >= min_area and c["count"] >= min_strokes):
            valid_rects.append(r)
    return valid_rects

# ==========================================
# GERAÇÃO GEMINI: PROMPTS ATUALIZADOS DA V34 E ND DA V36
# ==========================================
def generate_audiodescription(image_bytes):
    """Gera a audiodescrição utilizando a API (Prompt rigoroso da v34)"""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return "[AVISO: não foi possível ler esta imagem para gerar a descrição]"

    prompt = (
        """Você é um especialista em audiodescrição técnica para pessoas com deficiência visual. Sua tarefa é descrever o diagrama ou imagem de forma estritamente técnica, clara e estruturada.

DIRETRIZES DE DESCRIÇÃO:
Visão Geral: Comece sempre com um resumo macro do que a imagem representa (ex: tipo de diagrama, finalidade aparente) antes de detalhar as partes.
Detalhamento Lógico e Topológico: Descreva a topologia e as conexões seguindo um fluxo direcional claro (ex: da esquerda para a direita, ou da malha de entrada para a saída). Liste os componentes e seus valores exatos.
Estados e Representações Visuais: Relate explicitamente o estado físico ou visual dos componentes. Identifique alterações como fontes curto-circuitadas, terminais abertos, chaves abertas/fechadas ou marcações de medição.
Leitura de Tela (Acessibilidade): Escreva siglas, variáveis e fórmulas de forma estruturada. Separe letras maiúsculas com espaços (ex: 'V O C'). Para subscritos, escreva a palavra "índice" (ex: 'R índice T H' ou 'v índice L').
Fidelidade Absoluta: Não deduza, não resolva e não invente valores, conexões ou componentes que não estejam visualmente explícitos na imagem.

REGRA ESTRITA E ABSOLUTA: Retorne APENAS o texto contínuo da audiodescrição. É TERMINANTEMENTE PROIBIDO usar saudações, introduções, comentários, notas de encerramento ou qualquer formatação Markdown. Vá direto ao primeiro caractere.
Finalize com "TAGS VISUAIS:" listando os pontos críticos. Se não houver, coloque "TAGS VISUAIS: Nenhuma tag"."""
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        desc = response.text.strip()
        return desc if desc else "[AVISO: O modelo retornou uma descrição vazia.]"
    except Exception as e:
        return f"[AVISO: Falha na API do Gemini ({e}) — revise manualmente]"

def generate_audiodescription_nd(image_bytes, contexto_anterior=""):
    """Audiodescrição específica para Neurodivergência (Da v36)"""
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
2. Fluxo em Lista (Antidensidade): Descreva o funcionamento do circuito OBRIGATORIAMENTE como uma lista numerada passo a passo. NUNCA gere parágrafos blocados.
3. Topologia > Geometria (Orientação): É ESTRITAMENTE PROIBIDO usar termos espaciais ou visuais. Use APENAS referências topológicas.
4. Destaques Semânticos: Explique o *significado* de setas ou retângulos pontilhados.
5. Filtro de Ruído Absoluto: Ignore elementos puramente decorativos. Se for lixo visual, retorne EXATAMENTE "LIXO_VISUAL".
6. Formatação de Voz (TTS): Não use delimitadores LaTeX ($, ^, _). Use letras puras, como V1 e RL.

REGRA ESTRITA: Retorne APENAS a descrição. Sem markdown extra. 
Finalize obrigatoriamente com a linha "TAGS VISUAIS:" listando os conceitos críticos."""
    )

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        response = model.generate_content([prompt, pil_img])
        desc = response.text.strip()
        return desc if desc else "[AVISO: O modelo retornou uma descrição vazia.]"
    except Exception as e:
        return f"[AVISO: Falha na API do Gemini ({e}) — revise manualmente]"

def generate_latex_ocr(image_bytes):
    """Transcreve fórmula matemática para código LaTeX (Prompt estrito da v34)."""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        return None

    prompt = (
        """Você é um sistema automatizado de OCR matemático de altíssima precisão. Sua única função é transcrever fórmulas matemáticas presentes em imagens para código LaTeX válido.

DIRETRIZES DE TRANSCRIÇÃO:
Preservação Absoluta: Mantenha exatamente os símbolos, subíndices, sobrescritos, frações, variáveis e operadores. 
Matrizes e Estruturas Dimensionais: Respeite rigorosamente as dimensões apresentadas na imagem, utilizando ambientes corretos.
Texto em Fórmulas: Encapsule palavras no comando \\text{}.
Sem Alterações Analíticas: Não resolva as contas.
Múltiplas Equações: Utilize ambientes adequados como \\begin{aligned} ... \\end{aligned}.

REGRA ESTRITA E ABSOLUTA: Qualquer caractere que não seja código LaTeX puro causará erro fatal. Responda EXCLUSIVAMENTE com o código. É TERMINANTEMENTE PROIBIDO incluir marcações Markdown (```latex ... ```), cifrões ($ ou $$) ou explicações."""
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

    needs_api = profile in (AccessibilityProfile.LOW_VISION, AccessibilityProfile.BLINDNESS)
    is_cognitive = profile in (AccessibilityProfile.ADHD, AccessibilityProfile.DYSLEXIA, AccessibilityProfile.AUTISM)

    ultimo_contexto_diagrama = "" 

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        
        # TABELAS (V34)
        tabelas_encontradas = page.find_tables()
        bbox_tabelas = [tab.bbox for tab in tabelas_encontradas.tables] if tabelas_encontradas.tables else []

        blocks = page.get_text("dict")["blocks"]
        diagram_rects = detect_vector_diagrams(page) if (needs_api or is_cognitive) else []

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
                if not needs_api and not is_cognitive:
                    continue
                
                bbox_img = it["bbox"] if it["kind"] == "vector_diagram" else it["block"]["bbox"]
                
                # SOLUÇÃO ANTI-ALUCINAÇÃO IMAGEM (V34)
                if it["kind"] == "raster_image":
                    img_bbox = it["block"]["bbox"]
                    w = img_bbox[2] - img_bbox[0]
                    h = img_bbox[3] - img_bbox[1]
                    if w < 25 or h < 25:
                        continue 

                if it["kind"] == "vector_diagram":
                    img_bytes = rasterizar_regiao_pdf(page, it["bbox"], zoom=zoom_diagram)
                else:
                    img_bytes = it["block"]["image"]

                if needs_api:
                    is_equation_image = False
                    if it["kind"] == "raster_image":
                        aspect_ratio = w / h if h > 0 else 0
                        if aspect_ratio > 3.0:
                            is_equation_image = True

                    if is_equation_image:
                        time.sleep(4.1) 
                        latex_code = generate_latex_ocr(img_bytes)
                        if latex_code and validate_latex(latex_code):
                            processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "formula", "content": f"[FÓRMULA (OCR)]: $ {latex_code} $", "img_bytes": img_bytes})
                        else:
                            processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "aviso", "content": "[AVISO: FÓRMULA ILEGÍVEL]", "img_bytes": img_bytes})
                    else:
                        time.sleep(4.1)
                        desc = generate_audiodescription(img_bytes)
                        processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "audiodescricao", "content": f"[AUDIODESCRIÇÃO]: {desc}", "img_bytes": img_bytes})
                
                elif is_cognitive:
                    time.sleep(4.1)
                    desc_cognitiva = generate_audiodescription_nd(img_bytes, ultimo_contexto_diagrama)
                    
                    if "LIXO_VISUAL" in desc_cognitiva:
                        continue
                        
                    desc_cognitiva = sanitizar_para_tts(desc_cognitiva)
                    ultimo_contexto_diagrama = desc_cognitiva.split("TAGS VISUAIS:")[0].strip()
                    
                    processed_content.append({
                        "page_num": page_num, 
                        "bbox": bbox_img, 
                        "type": "audiodescricao",
                        "content": f"[APOIO CONCEITUAL]:\n{desc_cognitiva}", 
                        "img_bytes": img_bytes
                    })
                continue

            block = it["block"]
            text_block = "".join(span["text"] + " " for line in block["lines"] for span in line["spans"])
            bbox_txt = block['bbox']
            
            # SOLUÇÃO LIQUID PAPER (V34)
            if re.search(r'W{2,}', text_block) or "M WW" in text_block:
                processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "lixo_visual", "content": ""})
                continue 
            
            if id(block) in consumed_ids:
                continue

            altura = bbox_txt[3] - bbox_txt[1]
            letras_normais = count_letters(text_block)
            
            # BUG DO UNDERLINE (V34 Regex ajustada)
            simbolos_mat = len(re.findall(r'[0-9=\+\-\/\(\)\[\]\{\}\^]', text_block))
            
            parece_data_hora = bool(re.search(r'\d{2}/\d{2}|\d{2}:\d{2}', text_block))
            is_math = (simbolos_mat > 3) and (letras_normais < 30) and (len(text_block) < 150) and not parece_data_hora
            
            # ESCUDO DE TABELA PARA TEXTOS (V34)
            for tb in bbox_tabelas:
                if _rects_overlap(bbox_txt, tb):
                    is_math = False
                    break

            is_diagram_like = (not is_math) and altura > 100 and len(text_block) < 200

            if is_math:
                cleaned = clean_text_artifacts(text_block)
                if needs_api and looks_garbled(cleaned):
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_math)
                    time.sleep(4.1)
                    latex_code = generate_latex_ocr(img_bytes)
                    if latex_code and validate_latex(latex_code):
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "formula", "content": f"[FÓRMULA LATEX]: $ {latex_code} $"})
                    else:
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "aviso", "content": f"[FÓRMULA ILEGÍVEL]: {cleaned}"})
                else:
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "formula", "content": f"[FÓRMULA]: {cleaned}"})

            elif is_diagram_like:
                if needs_api:
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_diagram)
                    time.sleep(4.1)
                    desc = generate_audiodescription(img_bytes)
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "audiodescricao", "content": f"[DIAGRAMA]: {desc}", "img_bytes": img_bytes})
                else:
                    cleaned = clean_text_artifacts(text_block)
                    if cleaned:
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "texto_normal", "content": cleaned})
            else:
                cleaned = clean_text_artifacts(text_block)
                if cleaned:
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "texto_normal", "content": cleaned})

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
        
        # MÁGICA DO LIQUID PAPER (V34/36)
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
            
        annot.update()
        
    buff = io.BytesIO()
    doc.save(buff)
    return buff.getvalue()

def main():
    st.sidebar.title("EduAccess Pro - Unificado")
    sel_profile = st.sidebar.selectbox("Necessidade", [p.value for p in AccessibilityProfile])
    profile = AccessibilityProfile(sel_profile)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ajustes de Leitura")
    f_size = st.sidebar.slider("Tamanho Fonte (Pré-visualização)", 10, 30, 14) 

    with st.sidebar.expander("Configurações avançadas"):
        max_pages = st.slider("Máximo de páginas a processar", 1, 30, 15)
        zoom_diagram = st.slider("Zoom para diagramas", 1.0, 4.0, 2.0, 0.5)
        zoom_math = st.slider("Zoom para fórmulas", 1.0, 5.0, 3.0, 0.5)

    col1, col2 = st.columns(2)
    with col1:
        up = st.file_uploader("Upload do Material (PDF)", type=['pdf'])
        if st.button("PROCESSAR MATERIAL"):
            if up:
                prog_bar = st.progress(0)
                original_pdf_bytes = up.read() 
                
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
            st.text_area("Pré-visualização do Conteúdo:", texto_para_tela, height=500)

            if st.button("🔊 Ouvir Adaptação"):
                with st.spinner("Sintetizando áudio..."):
                    tts = gTTS(text=texto_para_tela, lang='pt', tld='com.br')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    st.audio(audio_fp, format='audio/mp3')

            if "original_pdf_bytes" in st.session_state:
                if profile in [AccessibilityProfile.ADHD, AccessibilityProfile.DYSLEXIA, AccessibilityProfile.AUTISM]:
                    pdf_bytes_final = build_accessible_pdf(st.session_state.adapted_data, profile)
                    nome_arquivo = f"adaptado_{profile.name}.pdf"
                    st.download_button(f"Exportar PDF Acessível ({profile.name})", pdf_bytes_final, nome_arquivo, "application/pdf")
                else:
                    pdf_bytes_final = inject_annotations_into_pdf(st.session_state.original_pdf_bytes, st.session_state.adapted_data)
                    st.download_button("Exportar PDF com Anotações", pdf_bytes_final, "adaptado.pdf", "application/pdf")

if __name__ == "__main__":
    main()