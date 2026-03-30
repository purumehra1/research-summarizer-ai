import streamlit as st
import os
import requests
import PyPDF2
import io
import re

st.set_page_config(page_title="Research Summarizer AI", page_icon="📚", layout="wide")
st.title("📚 Research Paper Summarizer AI")
st.caption("Paste any arXiv link or upload a PDF — understand any paper in 60 seconds.")

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

SAMPLE_ABSTRACT = """Attention Is All You Need (Vaswani et al., 2017)
We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature."""

def fetch_arxiv(url):
    arxiv_id = None
    match = re.search(r'arxiv.org/(?:abs|pdf)/([\d.]+)', url)
    if match:
        arxiv_id = match.group(1)
    if not arxiv_id:
        return None, None
    api_url = f"https://export.arxiv.org/abs/{arxiv_id}"
    try:
        resp = requests.get(api_url, timeout=10)
        title_match = re.search(r'<title>(.*?)</title>', resp.text, re.DOTALL)
        abstract_match = re.search(r'<blockquote[^>]*>(.*?)</blockquote>', resp.text, re.DOTALL)
        title = title_match.group(1).strip().replace('\n',' ') if title_match else "Unknown"
        abstract = re.sub(r'<[^>]+>', '', abstract_match.group(1)).strip() if abstract_match else ""
        return title, abstract
    except:
        return None, None

def summarize(text, gemini_key):
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"""Analyze this research paper/abstract and provide a structured breakdown:

{text[:8000]}

Provide EXACTLY in this format:
TITLE: [paper title or "Unknown"]
FIELD: [research field]
SUMMARY1: [bullet point 1 - main contribution]
SUMMARY2: [bullet point 2 - methodology]
SUMMARY3: [bullet point 3 - key result]
SUMMARY4: [bullet point 4 - significance]
SUMMARY5: [bullet point 5 - limitations/future work]
METHODOLOGY: [2-3 sentences on how they did it]
FINDINGS: [2-3 sentences on what they found]
ELI18: [Plain English explanation - imagine explaining to a smart 18-year-old with no research background. 3-4 sentences.]
IMPACT: [Why does this matter? Real-world applications. 2 sentences.]"""
            resp = model.generate_content(prompt)
            return resp.text
        except Exception as e:
            return f"API_ERROR: {e}"
    else:
        return """TITLE: Attention Is All You Need
FIELD: Natural Language Processing / Deep Learning
SUMMARY1: Introduces the Transformer architecture — a model based purely on attention mechanisms, removing the need for recurrent or convolutional networks.
SUMMARY2: Uses multi-head self-attention to process all positions in a sequence simultaneously, enabling much faster parallel training.
SUMMARY3: Achieves state-of-the-art BLEU scores on English-German (28.4) and English-French (41.8) translation benchmarks.
SUMMARY4: Significantly reduces training time compared to previous LSTM-based models — 3.5 days vs weeks.
SUMMARY5: Limited to sequence-to-sequence tasks in this paper; scalability to very long sequences was an open question.
METHODOLOGY: The model uses an encoder-decoder structure where both components use stacked self-attention and feedforward layers. Multi-head attention allows the model to jointly attend to different representation subspaces at different positions.
FINDINGS: Transformers outperform all previous architectures on machine translation benchmarks with a fraction of the compute. The attention mechanism enables better long-range dependency modeling than RNNs.
ELI18: Imagine you're translating a sentence. Old AI models read word by word like a human. This paper's AI reads ALL words at the same time and figures out which words are most related to each other — like seeing the whole chessboard at once instead of one square at a time. This made translation much faster and more accurate.
IMPACT: This paper became the foundation for GPT, BERT, ChatGPT, and virtually every modern AI language model. It fundamentally changed how AI processes language and is one of the most cited papers in AI history."""

def parse_summary(text):
    result = {}
    keys = ['TITLE','FIELD','SUMMARY1','SUMMARY2','SUMMARY3','SUMMARY4','SUMMARY5',
            'METHODOLOGY','FINDINGS','ELI18','IMPACT']
    lines = text.split('\n')
    for line in lines:
        for k in keys:
            if line.startswith(k+':'):
                result[k] = line[len(k)+1:].strip()
    return result

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Input Paper")
    input_mode = st.radio("Source", ["arXiv URL", "PDF Upload", "Paste Text", "Sample Paper"])
    
    paper_text = ""
    
    if input_mode == "arXiv URL":
        url = st.text_input("arXiv URL", placeholder="https://arxiv.org/abs/1706.03762")
        if url and st.button("Fetch Paper"):
            with st.spinner("Fetching from arXiv..."):
                title, abstract = fetch_arxiv(url)
            if abstract:
                paper_text = f"{title}\n\n{abstract}"
                st.success(f"Fetched: {title[:60]}...")
            else:
                st.error("Could not fetch. Try pasting the abstract manually.")
    
    elif input_mode == "PDF Upload":
        pdf = st.file_uploader("Upload PDF", type=['pdf'])
        if pdf:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf.read()))
            paper_text = " ".join([p.extract_text() or "" for p in reader.pages[:8]])
            st.success(f"Extracted {len(paper_text.split())} words")
    
    elif input_mode == "Paste Text":
        paper_text = st.text_area("Paste abstract or full text", height=250)
    
    else:
        paper_text = SAMPLE_ABSTRACT
        st.text_area("Sample Paper", SAMPLE_ABSTRACT, height=200)
    
    if not GEMINI_KEY:
        key_in = st.text_input("Gemini API Key (optional — demo works without it)", type="password")
        active_key = key_in
    else:
        active_key = GEMINI_KEY
    
    summarize_btn = st.button("📚 Summarize Paper", type="primary", disabled=not paper_text)

with col2:
    if summarize_btn and paper_text:
        with st.spinner("Analyzing paper..."):
            raw = summarize(paper_text, active_key)
            parsed = parse_summary(raw)
        
        st.subheader(parsed.get('TITLE', 'Research Paper'))
        st.caption(f"Field: {parsed.get('FIELD', 'Unknown')}")
        
        st.subheader("5-Point Summary")
        for i in range(1, 6):
            pt = parsed.get(f'SUMMARY{i}', '')
            if pt:
                st.write(f"**{i}.** {pt}")
        
        tab1, tab2, tab3 = st.tabs(["Methodology", "Findings", "Plain English"])
        with tab1:
            st.write(parsed.get('METHODOLOGY', ''))
        with tab2:
            st.write(parsed.get('FINDINGS', ''))
        with tab3:
            st.info(parsed.get('ELI18', ''))
            st.write("**Real-world impact:**", parsed.get('IMPACT', ''))
    else:
        st.info("Select a paper source and click Summarize to get started.")

st.caption("Puru Mehra | github.com/purumehra1/research-summarizer-ai")
