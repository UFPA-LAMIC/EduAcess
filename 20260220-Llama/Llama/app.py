# app.py - EduAccess Pro v34 (Gemini 3.5 Flash Only - Sem PyTorch/pix2tex)
import os
import time
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
        """Você é um especialista em audiodescrição técnica para pessoas com deficiência visual. Sua tarefa é descrever o diagrama ou imagem de forma estritamente técnica, clara e estruturada.

DIRETRIZES DE DESCRIÇÃO:

Visão Geral: Comece sempre com um resumo macro do que a imagem representa (ex: tipo de diagrama, finalidade aparente) antes de detalhar as partes.

Detalhamento Lógico e Topológico: Descreva a topologia e as conexões seguindo um fluxo direcional claro (ex: da esquerda para a direita, ou da malha de entrada para a saída). Liste os componentes e seus valores exatos.

Estados e Representações Visuais: Relate explicitamente o estado físico ou visual dos componentes. Identifique alterações como fontes curto-circuitadas (linhas contínuas espessas substituindo o componente), terminais abertos, chaves abertas/fechadas ou marcações de medição (setas, polaridades).

Leitura de Tela (Acessibilidade): Escreva siglas, variáveis e fórmulas de forma estruturada para a pronúncia correta de leitores de tela. Separe letras maiúsculas com espaços (ex: 'V O C'). Para subscritos, escreva a palavra "índice" (ex: 'R índice T H' ou 'v índice L').

Fidelidade Absoluta: Não deduza, não resolva e não invente valores, conexões ou componentes que não estejam visualmente explícitos na imagem.

REGRA ESTRITA E ABSOLUTA: Retorne APENAS o texto contínuo da audiodescrição. É TERMINANTEMENTE PROIBIDO usar saudações, introduções, comentários, notas de encerramento ou qualquer formatação Markdown (sem negrito, sem itálico, sem listas com asteriscos). Vá direto ao primeiro caractere do conteúdo."""
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
        """Você é um sistema automatizado de OCR matemático de altíssima precisão. Sua única função é transcrever fórmulas matemáticas presentes em imagens para código LaTeX válido.

DIRETRIZES DE TRANSCRIÇÃO:

Preservação Absoluta: Mantenha exatamente os símbolos, subíndices, sobrescritos, frações, variáveis e operadores físicos/matemáticos como aparecem na imagem. 

Matrizes e Estruturas Dimensionais: Para matrizes e vetores, respeite rigorosamente as dimensões apresentadas na imagem (ex.: 3x3, 2x2) e o alinhamento dos elementos, utilizando os ambientes corretos (como pmatrix, bmatrix ou vmatrix). Não omita nenhum elemento.

Texto em Fórmulas: Se houver palavras ou texto puro no meio da equação, encapsule-os obrigatoriamente no comando \text{} para não quebrar a formatação matemática.

Sem Alterações Analíticas: Não resolva as contas, não simplifique expressões, não corrija possíveis erros matemáticos da imagem e não invente símbolos.

Múltiplas Equações: Se houver mais de uma linha de fórmulas interdependentes, utilize ambientes adequados como \begin{aligned} ... \end{aligned} ou separe-as utilizando as quebras de linha padrão do LaTeX (\\).

REGRA ESTRITA E ABSOLUTA: O seu output será injetado diretamente em um parser de sistema. Qualquer caractere que não seja código LaTeX puro causará um erro fatal. Responda EXCLUSIVAMENTE com o código. É TERMINANTEMENTE PROIBIDO incluir marcações de bloco de código (```latex ... ```), delimitadores de ambiente inline ou display (como $ ou $$), palavras introdutórias (como 'Aqui está'), explicações, saudações ou comentários. Retorne apenas a string do código pronta para compilação."""
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

def generate_table_html(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        prompt = (
            "Você é um extrator de dados focado em acessibilidade. Transcreva esta imagem de tabela estritamente para formato Markdown. "
            "Mantenha as linhas e colunas exatas. É TERMINANTEMENTE PROIBIDO adicionar introduções, explicações ou notas. Retorne apenas a tabela."
        )
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        return model.generate_content([prompt, pil_img]).text.strip()
    except Exception:
        return "[AVISO: Falha ao transcrever tabela]"

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
        # Dentro do extract_dla_pipeline, no início do loop for page_num in range(total_pages):
        page = doc.load_page(page_num)

        # 1. Encontra as tabelas reais da página
        tabelas_encontradas = page.find_tables()
        bbox_tabelas = [tab.bbox for tab in tabelas_encontradas.tables] if tabelas_encontradas.tables else []

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
                
                bbox_img = it["bbox"] if it["kind"] == "vector_diagram" else it["block"]["bbox"]

                is_equation_image = False
                if it["kind"] == "raster_image":
                    img_bbox = it["block"]["bbox"]
                    w = img_bbox[2] - img_bbox[0]
                    h = img_bbox[3] - img_bbox[1]
                    
                    # 💡 SOLUÇÃO 1: ANTI-ALUCINAÇÃO
                    # Se a imagem for minúscula (como a checkbox ☑), ignore-a completamente.
                    if w < 25 or h < 25:
                        continue 
                    
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio > 3.0:
                        is_equation_image = True

                if is_equation_image:
                    img_bytes = it["block"]["image"]
                    time.sleep(4.1) 
                    latex_code = generate_latex_ocr(img_bytes)

                    if latex_code and validate_latex(latex_code):
                        processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "formula", "content": f"[FÓRMULA (OCR DE IMAGEM)]: $ {latex_code} $"})
                    else:
                        processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "aviso", "content": "[AVISO: FÓRMULA EM IMAGEM ILEGÍVEL]"})
                else:
                    if it["kind"] == "vector_diagram":
                        img_bytes = rasterizar_regiao_pdf(page, it["bbox"], zoom=zoom_diagram)
                    else:
                        img_bytes = it["block"]["image"]

                    time.sleep(4.1)
                    desc = generate_audiodescription(img_bytes)
                    processed_content.append({"page_num": page_num, "bbox": bbox_img, "type": "audiodescricao", "content": f"[AUDIODESCRIÇÃO DA IMAGEM]: {desc}"})
                continue

            block = it["block"]
            
            # Precisamos extrair o texto AQUI em cima para poder checar o lixo antes de descartá-lo
            text_block = "".join(span["text"] + " " for line in block["lines"] for span in line["spans"])
            bbox_txt = block['bbox']
            
            # 💡 SOLUÇÃO 2: O FILTRO DO "LIQUID PAPER" (Lixo Visual)
            # Se o texto tiver padrões estranhos de falha de circuito (WWW, M WW)
            if re.search(r'W{2,}', text_block) or "M WW" in text_block:
                processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "lixo_visual", "content": ""})
                continue # Some do leitor de tela e vai ser pintado de branco
            
            # Só depois do Liquid Paper checamos se ele pertence a um diagrama
            if id(block) in consumed_ids:
                continue

            altura = bbox_txt[3] - bbox_txt[1]

            letras_normais = count_letters(text_block)
            
            # 💡 SOLUÇÃO 3: O BUG DO UNDERLINE
            # Removido o \_ do final da regex. Agora a linha de assinatura será lida como texto normal.
            simbolos_mat = len(re.findall(r'[0-9=\+\-\/\(\)\[\]\{\}\^]', text_block))

            is_math = (simbolos_mat > 3) and (letras_normais < 30) and (len(text_block) < 150)
            is_math = (simbolos_mat > 3) and (letras_normais < 30) and (len(text_block) < 150)
            
            # 🛡️ NOVO: Se o texto colidir com uma tabela, force is_math para False
            for tb in bbox_tabelas:
                if _rects_overlap(bbox_txt, tb):
                    is_math = False
                    break
            
            is_diagram_like = (not is_math) and altura > 100 and len(text_block) < 200
            is_diagram_like = (not is_math) and altura > 100 and len(text_block) < 200

            if is_math:
                cleaned = clean_text_artifacts(text_block)
                if needs_visual_desc and looks_garbled(cleaned):
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_math)
                    
                    time.sleep(4.1)
                    latex_code = generate_latex_ocr(img_bytes)

                    if latex_code and validate_latex(latex_code):
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "formula", "content": f"[FÓRMULA LATEX (OCR)]: $ {latex_code} $"})
                    else:
                        processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "aviso", "content": f"[FÓRMULA - texto original ilegível, revisar manualmente]: {cleaned}"})
                else:
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "formula", "content": f"[FÓRMULA]: {cleaned}"})

            elif is_diagram_like:
                if needs_visual_desc:
                    img_bytes = rasterizar_regiao_pdf(page, bbox_txt, zoom=zoom_diagram)
                    
                    time.sleep(4.1)
                    desc = generate_audiodescription(img_bytes)
                    processed_content.append({"page_num": page_num, "bbox": bbox_txt, "type": "audiodescricao", "content": f"[DIAGRAMA IDENTIFICADO]: {desc}"})
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
    """
    Abre o PDF original e injeta as descrições da IA como anotações.
    Também oculta textos sujos (Liquid Paper).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for elem in elements_data:
        # Pula texto normal
        if elem["type"] == "texto_normal":
            continue
            
        page = doc.load_page(elem["page_num"])
        rect = fitz.Rect(elem["bbox"])
        
        # --- A MÁGICA DO LIQUID PAPER ---
        if elem["type"] == "lixo_visual":
            # Desenha um retângulo branco sem bordas por cima do texto quebrado
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            continue
        
        # Cria a anotação para os itens normais (Áudio descrição, fórmulas, avisos)
        annot = page.add_text_annot(rect.top_left, elem["content"])
        
        if elem["type"] == "audiodescricao":
            annot.set_info(title="Áudio Descrição (IA)")
            annot.set_colors(stroke=(0.0, 0.5, 1.0)) # Azul
        
        elif elem["type"] == "formula":
            annot.set_info(title="Fórmula Adaptada")
            annot.set_colors(stroke=(1.0, 0.0, 0.0)) # Vermelho
            
        elif elem["type"] == "aviso":
            annot.set_info(title="Aviso de Acessibilidade")
            annot.set_colors(stroke=(1.0, 0.5, 0.0)) # Laranja
            
        annot.update()
        
    buff = io.BytesIO()
    doc.save(buff)
    return buff.getvalue()

def main():
    st.sidebar.title("EduAccess Pro v34")
    sel_profile = st.sidebar.selectbox("Necessidade", [p.value for p in AccessibilityProfile])
    profile = AccessibilityProfile(sel_profile)

    st.sidebar.markdown("---")
    
    # As opções de entrelinhas e padding não afetam mais o PDF (já que ele mantém o layout original), 
    # mas mantive o slider de fonte caso você ainda use no app web (ou pode remover essas 3 linhas depois)
    st.sidebar.subheader("Ajustes de Leitura")
    f_size = st.sidebar.slider("Tamanho Fonte (Pré-visualização)", 10, 30, 14) 

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
                
                # Salvamos os bytes originais para reutilizar depois sem erro de Stream
                original_pdf_bytes = up.read() 
                
                raw_data, warnings = extract_dla_pipeline(
                    original_pdf_bytes, profile, prog_bar,
                    max_pages=max_pages,
                    zoom_diagram=zoom_diagram, zoom_math=zoom_math,
                )
                st.session_state.adapted_data = raw_data
                st.session_state.warnings = warnings
                st.session_state.original_pdf_bytes = original_pdf_bytes # Guarda para a hora de exportar
                
                prog_bar.empty()
                st.rerun()
            else:
                st.warning("Selecione um arquivo PDF antes de processar.")

    with col2:
        if "warnings" in st.session_state and st.session_state.warnings:
            for w in st.session_state.warnings:
                st.warning(w)

        if "adapted_data" in st.session_state and st.session_state.adapted_data:
            
            # Reconstrói os textos para jogar na tela e pro TTS ler na ordem certa
            texto_para_tela = "\n\n".join([item["content"] for item in st.session_state.adapted_data])
            
            st.text_area("Pré-visualização do Conteúdo:", texto_para_tela, height=500)

            # --- BOTÃO DE ÁUDIO NATIVO (TTS) ---
            if st.button("🔊 Ouvir Adaptação"):
                with st.spinner("Sintetizando áudio..."):
                    tts = gTTS(text=texto_para_tela, lang='pt', tld='com.br')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    st.audio(audio_fp, format='audio/mp3')

            # --- EXPORTAÇÃO IN-PLACE ---
            if "original_pdf_bytes" in st.session_state:
                pdf_bytes_final = inject_annotations_into_pdf(st.session_state.original_pdf_bytes, st.session_state.adapted_data)
                st.download_button("Exportar PDF Acessível", pdf_bytes_final, "adaptado.pdf", "application/pdf")

if __name__ == "__main__":
    main()