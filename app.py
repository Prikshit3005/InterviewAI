import streamlit as st
from config.settings import APP_TITLE, APP_ICON, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
from src.services.resume_parser import ResumeParserService, ResumeParsingError

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Styling (Glassmorphism & Harmonious Dark/Light Theme)
# ---------------------------------------------------------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        /* Global Typography */
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }

        /* Modern Gradient Header Title */
        .header-container {
            background: linear-gradient(135deg, #6c5ce7, #a862ea);
            padding: 2.5rem;
            border-radius: 16px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 20px rgba(108, 92, 231, 0.15);
        }
        
        .header-title {
            font-size: 2.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        
        .header-subtitle {
            font-size: 1.1rem;
            font-weight: 300;
            opacity: 0.9;
        }

        /* Premium Glassmorphic Cards */
        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        /* Success and Info Alerts Styles */
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .status-success {
            background-color: rgba(46, 213, 115, 0.15);
            color: #2ed573;
            border: 1px solid rgba(46, 213, 115, 0.3);
        }
        
        /* Custom scrollbar for text output */
        .text-output-container {
            background-color: #0f111a;
            color: #a6adbb;
            font-family: 'Courier New', Courier, monospace;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #1f2438;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-size: 0.9rem;
            line-height: 1.5;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Sidebar Navigation & Instructions
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric-line/100/6c5ce7/artificial-intelligence.png", width=70)
    st.title("Interview Hub")
    st.markdown("---")
    st.markdown("### **Milestone 1 Scope**")
    st.info(
        "Currently in Phase 1: local PDF upload & raw text extraction. "
        "Gemini integration and adaptive questioning are disabled for this preview."
    )
    st.markdown("---")
    st.markdown("### **How it works:**")
    st.markdown(
        "1. Upload a text-based resume in PDF format.\n"
        "2. PyMuPDF processes the file to extract text lines.\n"
        "3. Review the extracted text to check structure and readability."
    )

# ---------------------------------------------------------
# Main Page Layout
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="header-container">
        <div class="header-title">{APP_ICON} {APP_TITLE}</div>
        <div class="header-subtitle">Analyze your resume and extract plain text to prepare for AI-driven interviews.</div>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns([1, 1], gap="medium")

with col1:
    st.markdown("### 📤 Upload Resume")
    st.markdown(
        f"Please upload your technical resume. Supported format: **PDF** (Max {MAX_FILE_SIZE_MB}MB)."
    )

    # File uploader interface
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=ALLOWED_EXTENSIONS,
        help="Make sure the PDF contains readable text, not scanned images."
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        # Display File Details Card
        st.markdown(
            f"""
            <div class="glass-card">
                <strong>📄 File Name:</strong> {uploaded_file.name}<br>
                <strong>⚖️ File Size:</strong> {file_size_mb:.2f} MB
            </div>
            """,
            unsafe_allow_html=True
        )

        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB}MB.")
        else:
            # Action button to trigger parsing
            if st.button("Extract Resume Text", type="primary", use_container_width=True):
                with st.spinner("Extracting text using PyMuPDF..."):
                    try:
                        # Read raw bytes of the uploaded file
                        pdf_bytes = uploaded_file.read()
                        
                        # Call the parsing service
                        extracted_text = ResumeParserService.extract_text_from_bytes(pdf_bytes)
                        
                        # Store in session state to persist between page refreshes
                        st.session_state["extracted_text"] = extracted_text
                        st.session_state["parse_success"] = True
                        st.session_state["parse_error"] = None
                        
                    except ResumeParsingError as e:
                        st.session_state["extracted_text"] = None
                        st.session_state["parse_success"] = False
                        st.session_state["parse_error"] = str(e)
                    except Exception as e:
                        st.session_state["extracted_text"] = None
                        st.session_state["parse_success"] = False
                        st.session_state["parse_error"] = f"An unexpected system error occurred: {str(e)}"

# Display Results
with col2:
    st.markdown("### 🔍 Extraction Results")
    
    # Check if a parsing action has taken place
    if "parse_success" in st.session_state:
        if st.session_state["parse_success"]:
            st.markdown(
                '<div class="status-badge status-success">✓ Extraction Successful</div>', 
                unsafe_allow_html=True
            )
            
            # Display raw text inside custom styled text box
            text_val = st.session_state.get("extracted_text", "")
            st.markdown(
                f'<div class="text-output-container">{text_val}</div>',
                unsafe_allow_html=True
            )
            
            # Add a small download button for the raw text
            st.download_button(
                label="📥 Download Extracted Text (.txt)",
                data=text_val,
                file_name=f"{uploaded_file.name.split('.')[0]}_extracted.txt",
                mime="text/plain",
                use_container_width=True
            )
        elif st.session_state["parse_error"]:
            st.error(st.session_state["parse_error"])
            st.warning(
                "💡 **Tip:** Double check that your resume is not scanned or saved as an image. "
                "Try exporting it again directly from Microsoft Word, Google Docs, or LaTeX."
            )
    else:
        st.info("Upload a resume on the left and click 'Extract Resume Text' to view results here.")
