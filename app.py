import streamlit as st
from config.settings import APP_TITLE, APP_ICON, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS, DEFAULT_QUESTION_COUNT, DEV_MODE
from src.services.resume_parser import ResumeParserService, ResumeParsingError
from src.services.gemini_client import GeminiClientService, GeminiClientError
from src.services.interview_engine import InterviewEngine, InterviewEngineError
from src.services.evaluation_engine import EvaluationEngine, EvaluationEngineError
from src.models.interview_session import InterviewSession
import html

@st.cache_data(show_spinner=False)
def get_cached_profile(extracted_text: str):
    """
    Cached wrapper for resume profile structuring to prevent repeated Gemini API calls
    upon page reruns or layout refreshes.
    """
    return GeminiClientService.generate_profile(extracted_text)

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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* Reset and Global Styles */
        html, body, p, h1, h2, h3, h4, h5, h6, li, a, button, textarea, input, label {
            font-family: 'Inter', sans-serif !important;
        }
        
        .stApp {
            background-color: #09090B !important;
            background-image: 
                radial-gradient(circle at 50% -20%, rgba(139, 92, 246, 0.15), rgba(9, 9, 11, 0)),
                radial-gradient(circle at 0% 100%, rgba(168, 85, 247, 0.05), rgba(9, 9, 11, 0)) !important;
            background-attachment: fixed !important;
            color: #FAFAFA !important;
        }

        /* Animations */
        @keyframes fadeUp {
            from {
                opacity: 0;
                transform: translateY(16px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.97);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes borderPulse {
            0%, 100% { border-color: rgba(255, 255, 255, 0.08); }
            50% { border-color: rgba(139, 92, 246, 0.4); }
        }

        @keyframes pulseGreen {
            0% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
            }
            70% {
                transform: scale(1.1);
                box-shadow: 0 0 0 6px rgba(34, 197, 94, 0);
            }
            100% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
            }
        }

        @keyframes typing {
            0%, 100% { opacity: 0.2; }
            50% { opacity: 1; }
        }

        .animate-fadeup {
            animation: fadeUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        
        .animate-fadein {
            animation: fadeIn 0.3s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        
        .animate-scalein {
            animation: scaleIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        /* Sidebar Styling Overrides */
        [data-testid="stSidebar"] {
            background-color: #111113 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        /* Premium Header Styling */
        .premium-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 2rem;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 20px;
            margin-bottom: 2.5rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            animation: fadeUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .header-logo-bg {
            background: linear-gradient(135deg, #8B5CF6, #A855F7);
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3);
        }

        .header-title-text {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #FAFAFA;
            margin: 0;
            line-height: 1.2;
        }

        .header-subtitle-text {
            font-size: 0.875rem;
            color: #A1A1AA;
            margin: 0;
        }

        .header-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(34, 197, 94, 0.08);
            border: 1px solid rgba(34, 197, 94, 0.2);
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #22C55E;
        }

        .green-dot {
            width: 8px;
            height: 8px;
            background-color: #22C55E;
            border-radius: 50%;
            display: inline-block;
            animation: pulseGreen 1.8s infinite ease-in-out;
        }

        /* Sidebar Custom Widgets */
        .sidebar-glass-card {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            border-radius: 14px !important;
            padding: 1rem !important;
            margin-bottom: 1rem !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        .sidebar-glass-card:hover {
            background: rgba(255, 255, 255, 0.05) !important;
            border-color: rgba(139, 92, 246, 0.2) !important;
            transform: translateY(-2px);
        }
        .sidebar-card-label {
            font-size: 0.72rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.75px !important;
            color: #A1A1AA !important;
            font-weight: 600 !important;
        }
        .sidebar-card-value {
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            color: #FAFAFA !important;
            margin-top: 0.3rem !important;
        }
        .sidebar-progress-bg {
            background: rgba(255, 255, 255, 0.06) !important;
            border-radius: 6px !important;
            height: 6px !important;
            width: 100% !important;
            overflow: hidden !important;
            margin-top: 0.5rem !important;
        }
        .sidebar-progress-fill {
            background: linear-gradient(90deg, #8B5CF6, #A855F7) !important;
            height: 100% !important;
            border-radius: 6px !important;
            transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        .sidebar-stat-row {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            font-size: 0.8rem !important;
            color: #FAFAFA !important;
            margin-top: 0.5rem !important;
        }
        .sidebar-stat-row span:first-child {
            color: #A1A1AA !important;
        }
        .sidebar-activity-item {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            font-size: 0.78rem !important;
            color: #A1A1AA !important;
            margin-top: 0.5rem !important;
        }
        .sidebar-activity-dot {
            width: 5px !important;
            height: 5px !important;
            border-radius: 50% !important;
            background-color: #8B5CF6 !important;
        }

        /* Glassmorphic Main Layout Cards */
        .glass-card {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        .glass-card:hover {
            transform: translateY(-2px);
            border-color: rgba(139, 92, 246, 0.2) !important;
            box-shadow: 0 8px 30px rgba(139, 92, 246, 0.08) !important;
        }

        /* File Uploader Custom Styles */
        [data-testid="stFileUploader"] {
            background-color: rgba(255, 255, 255, 0.01) !important;
            border: 2px dashed rgba(255, 255, 255, 0.08) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
            animation: borderPulse 4s infinite ease-in-out;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: #8B5CF6 !important;
            background-color: rgba(139, 92, 246, 0.02) !important;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.1) !important;
        }
        [data-testid="stFileUploader"] section {
            background-color: transparent !important;
            padding: 0 !important;
        }
        [data-testid="stFileUploader"] button {
            background-color: rgba(255, 255, 255, 0.06) !important;
            color: #FAFAFA !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            transition: all 0.25s !important;
        }
        [data-testid="stFileUploader"] button:hover {
            background-color: rgba(255, 255, 255, 0.12) !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }

        /* Profile & Candidate Sections */
        .profile-container {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.06);
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 1.5rem;
        }

        .avatar-circle {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #8B5CF6, #A855F7);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        }

        .profile-name {
            font-size: 1.25rem;
            font-weight: 600;
            color: #FAFAFA;
            margin: 0;
        }

        .profile-meta {
            font-size: 0.85rem;
            color: #A1A1AA;
            margin-top: 2px;
        }

        /* Skill Tag / Pills */
        .skill-tag {
            background-color: rgba(139, 92, 246, 0.08) !important;
            color: #A855F7 !important;
            padding: 5px 14px !important;
            border-radius: 30px !important;
            margin: 4px !important;
            display: inline-block !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            border: 1px solid rgba(139, 92, 246, 0.2) !important;
            transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        .skill-tag:hover {
            transform: scale(1.05);
            background-color: rgba(139, 92, 246, 0.15) !important;
            border-color: rgba(139, 92, 246, 0.4) !important;
            box-shadow: 0 0 12px rgba(139, 92, 246, 0.2) !important;
        }

        /* Timeline and Project Cards */
        .timeline-container {
            position: relative;
            padding-left: 20px;
            border-left: 2px solid rgba(255, 255, 255, 0.08);
            margin-left: 10px;
            margin-top: 1rem;
        }

        .timeline-item {
            position: relative;
            margin-bottom: 1.25rem;
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -26px;
            top: 6px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #8B5CF6;
            border: 2px solid #09090B;
        }

        .timeline-title {
            font-size: 0.9rem;
            font-weight: 600;
            color: #FAFAFA;
        }

        .timeline-desc {
            font-size: 0.8rem;
            color: #A1A1AA;
            margin-top: 2px;
        }

        .project-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .project-card:hover {
            transform: translateY(-2px);
            border-color: rgba(139, 92, 246, 0.15);
            background: rgba(255, 255, 255, 0.03);
        }

        /* Interview Page Specifics */
        .question-box {
            background: rgba(139, 92, 246, 0.04) !important;
            border: 1px solid rgba(139, 92, 246, 0.15) !important;
            padding: 1.5rem !important;
            border-radius: 16px !important;
            margin-bottom: 1.5rem !important;
            position: relative !important;
            backdrop-filter: blur(8px) !important;
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.05) !important;
        }
        
        .ai-avatar-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            color: #8B5CF6;
            text-transform: uppercase;
            letter-spacing: 1px;
            background: rgba(139, 92, 246, 0.08);
            padding: 4px 10px;
            border-radius: 30px;
            margin-bottom: 0.75rem;
        }
        
        .question-meta-bar {
            display: flex;
            gap: 12px;
            margin-top: 1rem;
            font-size: 0.78rem;
            color: #A1A1AA;
        }

        .meta-badge {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 3px 10px;
            border-radius: 30px;
            font-weight: 500;
        }

        /* Typing Indicator Simulation */
        .typing-dots {
            display: inline-flex;
            gap: 4px;
            align-items: center;
        }
        .typing-dot {
            width: 6px;
            height: 6px;
            background-color: #8B5CF6;
            border-radius: 50%;
            animation: typing 1s infinite ease-in-out;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        /* Streamlit Element Styling Overrides */
        textarea[data-testid="stTextArea"] {
            background-color: #111113 !important;
            color: #FAFAFA !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
            line-height: 1.6 !important;
            font-family: 'Inter', sans-serif !important;
        }
        textarea[data-testid="stTextArea"]:focus {
            border-color: #8B5CF6 !important;
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.25) !important;
            outline: none !important;
        }

        /* Buttons Styling */
        button[data-testid="baseButton-primary"], 
        button[data-testid="baseButton-primaryFormSubmit"] {
            background: linear-gradient(135deg, #8B5CF6, #A855F7) !important;
            color: #FAFAFA !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.8rem !important;
            font-weight: 600 !important;
            font-family: 'Inter', sans-serif !important;
            box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3) !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        button[data-testid="baseButton-primary"]:hover, 
        button[data-testid="baseButton-primaryFormSubmit"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5) !important;
            opacity: 0.95;
        }
        button[data-testid="baseButton-primary"]:active,
        button[data-testid="baseButton-primaryFormSubmit"]:active {
            transform: translateY(0px) !important;
        }

        button[data-testid="baseButton-secondary"], 
        button[data-testid="baseButton-secondaryFormSubmit"] {
            background-color: rgba(255, 255, 255, 0.04) !important;
            color: #FAFAFA !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.8rem !important;
            font-weight: 500 !important;
            font-family: 'Inter', sans-serif !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
        }
        button[data-testid="baseButton-secondary"]:hover, 
        button[data-testid="baseButton-secondaryFormSubmit"]:hover {
            background-color: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 255, 255, 0.15) !important;
            transform: translateY(-2px) !important;
            color: #FAFAFA !important;
        }

        /* Streamlit Progress Bar */
        div[data-testid="stProgress"] > div > div > div > div {
            background: linear-gradient(90deg, #8B5CF6, #A855F7) !important;
            border-radius: 6px !important;
        }
        div[data-testid="stProgress"] {
            margin-bottom: 1.5rem !important;
        }

        /* Recruiter Dashboard Metrics */
        .metric-score-circle {
            position: relative;
            width: 140px;
            height: 140px;
            margin: 0 auto 1.5rem auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .metric-score-label {
            position: absolute;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .metric-score-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: #FAFAFA;
            line-height: 1;
        }

        .metric-score-caption {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #A1A1AA;
            margin-top: 4px;
        }

        /* Custom Status Badge */
        .status-badge {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 30px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 1rem;
            animation: fadeIn 0.3s ease-in-out;
        }
        
        .status-success {
            background-color: rgba(34, 197, 94, 0.08);
            color: #22C55E;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }

        .status-analysis {
            background-color: rgba(139, 92, 246, 0.08);
            color: #A855F7;
            border: 1px solid rgba(139, 92, 246, 0.2);
        }

        /* Recruiter Dashboard layout styling */
        .report-section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #FAFAFA;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-perf {
            background: rgba(255, 255, 255, 0.02) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            padding: 1.25rem !important;
            text-align: center !important;
            transition: all 0.25s ease !important;
        }
        
        .card-perf:hover {
            transform: translateY(-2px) !important;
            border-color: rgba(139, 92, 246, 0.2) !important;
            background: rgba(255, 255, 255, 0.03) !important;
        }

        /* Detailed Accordion overrides */
        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.02) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 10px !important;
            color: #FAFAFA !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
            padding: 0.75rem 1rem !important;
        }
        .streamlit-expanderHeader:hover {
            background-color: rgba(255, 255, 255, 0.04) !important;
            border-color: rgba(139, 92, 246, 0.15) !important;
        }
        .streamlit-expanderContent {
            background-color: rgba(255, 255, 255, 0.01) !important;
            border-left: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-bottom-left-radius: 10px !important;
            border-bottom-right-radius: 10px !important;
            padding: 1.25rem !important;
        }

        /* Custom scrollbar */
        .text-output-container {
            background-color: #111113 !important;
            color: #A1A1AA !important;
            font-family: 'Inter', sans-serif !important;
            padding: 1.25rem !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            max-height: 250px !important;
            overflow-y: auto !important;
            white-space: pre-wrap !important;
            font-size: 0.85rem !important;
            line-height: 1.6 !important;
            margin-bottom: 1.5rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Sidebar Navigation & Instructions
# ---------------------------------------------------------
with st.sidebar:
    # Logo & Brand Header
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 2rem; padding: 0.5rem 0.25rem;">
            <div class="header-logo-bg" style="width: 40px; height: 40px; border-radius: 10px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white"/>
                    <path d="M2 17L12 22L22 17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #FAFAFA; letter-spacing: -0.5px; line-height: 1.2;">Interview Hub</div>
                <div style="font-size: 0.7rem; color: #A1A1AA;">AI Recruiter Suite</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # State evaluation
    session = st.session_state.get("interview_session")
    if session is not None:
        try:
            session = InterviewSession(**session.model_dump())
            st.session_state["interview_session"] = session
        except Exception:
            pass
    if session is None:
        phase = "Setup & Profile"
        progress_pct = 0
        progress_text = "Awaiting Resume"
        has_profile = "✓ Structured" if st.session_state.get("candidate_profile") else "✗ Pending"
        stats_html = f"""
        <div class="sidebar-stat-row">
            <span>Resume Parsing</span>
            <span>{"✓ Active" if st.session_state.get("extracted_text") else "✗ Empty"}</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Candidate Profile</span>
            <span>{has_profile}</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Target Questions</span>
            <span>{DEFAULT_QUESTION_COUNT}</span>
        </div>
        """
        recent_activity = ["System initialized", "Ready for resume upload"]
    elif not session.is_completed:
        phase = "Interview Room"
        curr_idx = session.current_question_index
        total_q = DEFAULT_QUESTION_COUNT
        progress_pct = int((curr_idx / total_q) * 100)
        progress_text = f"Question {curr_idx + 1} of {total_q}"
        stats_html = f"""
        <div class="sidebar-stat-row">
            <span>Progress Status</span>
            <span>Answering</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Questions Complete</span>
            <span>{len(session.history)} / {total_q}</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Current Category</span>
            <span style="max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(session.questions[curr_idx].category)}">{html.escape(session.questions[curr_idx].category)}</span>
        </div>
        """
        recent_activity = [f"Answering Question {curr_idx + 1}", "Interview session started"]
    else:
        phase = "Evaluation Report"
        progress_pct = 100
        progress_text = "Completed"
        overall_score = session.report.overall_score if session.report else 0.0
        stats_html = f"""
        <div class="sidebar-stat-row">
            <span>Final Score</span>
            <span style="color: #22C55E; font-weight: 700;">{overall_score:.1f}%</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Evaluation Status</span>
            <span style="color: #22C55E; font-weight: 600;">✓ Calculated</span>
        </div>
        <div class="sidebar-stat-row">
            <span>History Saved</span>
            <span>Yes</span>
        </div>
        """
        recent_activity = ["Scorecard dashboard loaded", "Answers evaluated with Gemini"]

    activity_items = "".join([f'<div class="sidebar-activity-item"><div class="sidebar-activity-dot"></div><span>{act}</span></div>' for act in recent_activity])

    st.markdown(
        f"""
        <!-- Phase Card -->
        <div class="sidebar-glass-card">
            <div class="sidebar-card-label">Current Phase</div>
            <div class="sidebar-card-value" style="color: #8B5CF6;">{phase}</div>
        </div>
        
        <!-- Progress Bar Card -->
        <div class="sidebar-glass-card">
            <div class="sidebar-card-label">Progress</div>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem; margin-top: 0.25rem;">
                <span style="font-size: 0.8rem; font-weight: 500; color: #FAFAFA;">{progress_text}</span>
                <span style="font-size: 0.8rem; font-weight: 600; color: #8B5CF6;">{progress_pct}%</span>
            </div>
            <div class="sidebar-progress-bg">
                <div class="sidebar-progress-fill" style="width: {progress_pct}%;"></div>
            </div>
        </div>

        <!-- Interview Stats Card -->
        <div class="sidebar-glass-card">
            <div class="sidebar-card-label" style="margin-bottom: 0.5rem;">Interview Stats</div>
            {stats_html}
        </div>

        <!-- Recent Activity Card -->
        <div class="sidebar-glass-card">
            <div class="sidebar-card-label" style="margin-bottom: 0.5rem;">Recent Activity</div>
            {activity_items}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Active session actions
    if st.session_state.get("interview_session"):
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Abort Interview ❌", use_container_width=True):
            st.session_state["interview_session"] = None
            st.rerun()

# ---------------------------------------------------------
# Main Page Layout
# ---------------------------------------------------------
# Premium Header Component
st.markdown(
    """
    <div class="premium-header">
        <div class="header-left">
            <div class="header-logo-bg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white"/>
                    <path d="M2 17L12 22L22 17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div>
                <h1 class="header-title-text">InterviewAI</h1>
                <p class="header-subtitle-text">AI-powered Technical Interview Simulator</p>
            </div>
        </div>
        <div class="header-badge">
            <span class="green-dot"></span>
            Gemini Connected
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if DEV_MODE:
    from src.services.session_storage import SessionStorageService
    if not SessionStorageService.session_exists():
        st.warning("⚠️ No demo session found. Run one complete interview in Production Mode first.")

if st.session_state.get("interview_session") is None:
    # ---------------------------------------------------------
    # VIEW A: Setup, Parsing & Analysis Screen
    # ---------------------------------------------------------

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.markdown("### 📤 Upload & Process Resume")
        st.markdown(
            f"Upload a technical resume. Supported format: **PDF** (Max {MAX_FILE_SIZE_MB}MB)."
        )

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=ALLOWED_EXTENSIONS,
            help="Make sure the PDF contains readable text, not scanned images."
        )

        if uploaded_file is not None:
            if "current_file" not in st.session_state or st.session_state["current_file"] != uploaded_file.name:
                st.session_state["current_file"] = uploaded_file.name
                st.session_state["extracted_text"] = None
                st.session_state["candidate_profile"] = None
                if "parse_success" in st.session_state:
                    del st.session_state["parse_success"]
                if "parse_error" in st.session_state:
                    del st.session_state["parse_error"]
                if "analysis_error" in st.session_state:
                    del st.session_state["analysis_error"]

            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            
            st.markdown(
                f"""<div class="glass-card animate-scalein" style="display: flex; align-items: center; justify-content: space-between; border-left: 4px solid #22C55E !important;">
<div>
<div style="font-size: 0.75rem; text-transform: uppercase; color: #22C55E; font-weight: 700; letter-spacing: 0.5px;">✓ Resume Uploaded</div>
<div style="font-size: 1.05rem; font-weight: 600; color: #FAFAFA; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px;" title="{html.escape(uploaded_file.name)}">{html.escape(uploaded_file.name)}</div>
<div style="font-size: 0.78rem; color: #A1A1AA; margin-top: 2px;">File Size: {file_size_mb:.2f} MB</div>
</div>
<div style="background: rgba(34, 197, 94, 0.1); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(34, 197, 94, 0.2);">
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
<polyline points="20 6 9 17 4 12"></polyline>
</svg>
</div>
</div>""",
                unsafe_allow_html=True
            )

            if file_size_mb > MAX_FILE_SIZE_MB:
                st.error(f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB}MB.")
            else:
                if st.button("Extract Resume Text", type="primary", use_container_width=True):
                    with st.spinner("Extracting text using PyMuPDF..."):
                        try:
                            pdf_bytes = uploaded_file.read()
                            extracted_text = ResumeParserService.extract_text_from_bytes(pdf_bytes)
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
                            st.session_state["parse_error"] = f"An unexpected parsing error occurred: {str(e)}"

                if st.session_state.get("extracted_text"):
                    st.markdown("---")
                    st.markdown("### 🤖 Profile Analysis")
                    st.write("Convert raw text into a validated candidate profile using Gemini.")
                    
                    if st.button("Analyze Resume", type="secondary", use_container_width=True):
                        with st.spinner("Querying Gemini 2.5 Flash for structured data..."):
                            try:
                                # Query the cached profile generation to save API calls
                                profile = get_cached_profile(st.session_state["extracted_text"])
                                st.session_state["candidate_profile"] = profile
                                st.session_state["analysis_error"] = None
                            except GeminiClientError as e:
                                st.session_state["candidate_profile"] = None
                                st.session_state["analysis_error"] = str(e)
                            except Exception as e:
                                st.session_state["candidate_profile"] = None
                                st.session_state["analysis_error"] = f"An unexpected analysis error occurred: {str(e)}"
                    
                    if st.session_state.get("analysis_error"):
                        err_str = str(st.session_state["analysis_error"])
                        if "HTTP 429" in err_str or "quota" in err_str.lower():
                            st.error("⏳ **Gemini API Rate Limit Exceeded:** You have hit the API rate limits on your free tier key. Please wait about 60 seconds and click 'Analyze Resume' again.")
                        else:
                            st.error("❌ Failed to analyze resume. Please verify your Gemini API key and try again.")

    with col2:
        st.markdown("### 📊 Parsed Outputs")
        
        if st.session_state.get("candidate_profile"):
            profile = st.session_state["candidate_profile"]
            
            st.markdown(
                '<div class="status-badge status-analysis">✓ Profile Structured Successfully</div>', 
                unsafe_allow_html=True
            )
            
            initials = "".join([n[0].upper() for n in profile.name.split() if n])[:2] if profile.name else "AI"
            
            st.markdown(
                f"""<div class="profile-container animate-scalein">
<div class="avatar-circle">{html.escape(initials)}</div>
<div>
<div class="profile-name">{html.escape(profile.name)}</div>
<div class="profile-meta">📧 {html.escape(profile.email) if profile.email else "No email detected"}</div>
<div class="profile-meta">💼 Candidate Profile &bull; Verified</div>
</div>
</div>""",
                unsafe_allow_html=True
            )
            
            # Display Skills
            st.markdown("#### 🛠️ Core Skills")
            if profile.skills:
                skills_html = "".join([f'<span class="skill-tag">{html.escape(skill)}</span>' for skill in profile.skills])
                st.markdown(f"<div style='margin-bottom: 1.5rem;'>{skills_html}</div>", unsafe_allow_html=True)
            else:
                st.warning("No skills detected.")
                
            # Display Education
            st.markdown("#### 🎓 Education")
            if profile.education:
                edu_html = ""
                for edu in profile.education:
                    edu_html += f"""<div class="timeline-item">
<div class="timeline-title">{html.escape(edu)}</div>
<div class="timeline-desc">Academic Milestones</div>
</div>"""
                st.markdown(f'<div class="timeline-container">{edu_html}</div>', unsafe_allow_html=True)
            else:
                st.info("No education details detected.")

            # Display Projects
            st.markdown("#### 🚀 Key Projects")
            if profile.projects:
                proj_html = ""
                for proj in profile.projects:
                    proj_html += f"""<div class="project-card">
<div class="timeline-title">{html.escape(proj)}</div>
<div class="timeline-desc">Technical Project Portfolio</div>
</div>"""
                st.markdown(f'<div style="margin-bottom: 1.5rem;">{proj_html}</div>', unsafe_allow_html=True)
            else:
                st.info("No projects detected.")
                
            # Start simulated interview triggers
            st.markdown("---")
            st.markdown("### 🎯 Ready to Practice?")
            st.write("Start an interactive technical interview based on your profile skills.")
            if st.button("Start Simulated Interview 🚀", type="primary", use_container_width=True):
                with st.spinner("Preparing personalized technical interview questions..."):
                    try:
                        session = InterviewEngine.initialize_session(profile, DEFAULT_QUESTION_COUNT)
                        st.session_state["interview_session"] = session
                        st.rerun()
                    except InterviewEngineError as e:
                        st.error(f"Failed to generate questions: {e}")
                
        elif st.session_state.get("extracted_text"):
            st.markdown(
                '<div class="status-badge status-success">✓ Raw Text Loaded</div>', 
                unsafe_allow_html=True
            )
            st.warning("👉 **Next Step:** Click 'Analyze Resume' on the left to structure this text with Gemini.")
            
            st.markdown(
                f'<div class="text-output-container">{st.session_state["extracted_text"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("Upload a resume on the left and click 'Extract Resume Text' to view results here.")

else:
    # ---------------------------------------------------------
    # VIEW B: Active Interview Screen
    # ---------------------------------------------------------
    session: InterviewSession = st.session_state["interview_session"]

    if session.is_completed:
        # Check if we need to compile the report
        if session.report is None:
            with st.spinner("Analyzing responses and compiling technical performance report..."):
                try:
                    report = EvaluationEngine.generate_report(session)
                    session.report = report
                    st.session_state["interview_session"] = session
                    if not DEV_MODE:
                        from src.services.session_storage import SessionStorageService
                        SessionStorageService.save_session(
                            profile=st.session_state.get("candidate_profile"),
                            session=session,
                            state=st.session_state.get("interview_state"),
                            category_sequence=st.session_state.get("category_sequence"),
                            extracted_text=st.session_state.get("extracted_text")
                        )
                    st.rerun()
                except EvaluationEngineError as e:
                    err_str = str(e)
                    if "HTTP 429" in err_str or "quota" in err_str.lower():
                        st.error("⏳ **Gemini API Rate Limit Exceeded:** You have hit the API rate limits on your free tier key. Please wait about 60 seconds and click 'Retry Report Generation'.")
                    else:
                        st.error("Failed to compile final evaluation report. Please try again.")
                    if st.button("Retry Report Generation 🔄", use_container_width=True):
                        st.rerun()
        else:
            # ---------------------------------------------------------
            # VIEW C: Completed Evaluation Dashboard Report
            # ---------------------------------------------------------
            report = session.report
            
            # 1. Dashboard Summary Layout
            col_dash_1, col_dash_2 = st.columns([1, 2], gap="large")
            
            with col_dash_1:
                # Overall Score Circle Gauge
                circ = 339.3
                offset = circ - (report.overall_score / 100.0) * circ
                score_color = "#22C55E" if report.overall_score >= 80 else ("#F59E0B" if report.overall_score >= 60 else "#EF4444")
                st.markdown(
                    f"""
                    <div class="glass-card animate-scalein" style="text-align: center; padding: 1.5rem 1rem; margin-bottom: 1rem;">
                        <div class="metric-score-circle">
                            <svg width="140" height="140" viewBox="0 0 140 140" style="transform: rotate(-90deg);">
                                <circle cx="70" cy="70" r="54" fill="none" stroke="rgba(255, 255, 255, 0.04)" stroke-width="8"></circle>
                                <circle cx="70" cy="70" r="54" fill="none" stroke="url(#score-grad)" stroke-width="8" stroke-linecap="round" stroke-dasharray="339.3" stroke-dashoffset="{offset}" style="transition: stroke-dashoffset 1s ease-in-out;"></circle>
                                <defs>
                                    <linearGradient id="score-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stop-color="#8B5CF6"></stop>
                                        <stop offset="100%" stop-color="#A855F7"></stop>
                                    </linearGradient>
                                </defs>
                            </svg>
                            <div class="metric-score-label">
                                <div class="metric-score-value" style="color: {score_color};">{report.overall_score:.1f}%</div>
                                <div class="metric-score-caption">OVERALL SCORE</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Radar Chart Dynamic SVG
                score_map = {cat_score.category: cat_score.score for cat_score in report.category_scores}
                s1 = score_map.get("Resume & Projects", 70.0)
                s2 = score_map.get("AI/ML Concepts", 70.0)
                s3 = score_map.get("Software Engineering", 70.0)
                s4 = score_map.get("DSA & CS Fundamentals", 70.0)
                
                r_scale = 65
                p1_x = 100
                p1_y = 100 - r_scale * (s1 / 100.0)
                p2_x = 100 + r_scale * (s2 / 100.0)
                p2_y = 100
                p3_x = 100
                p3_y = 100 + r_scale * (s3 / 100.0)
                p4_x = 100 - r_scale * (s4 / 100.0)
                p4_y = 100
                
                st.markdown(
                    f"""
                    <div class="glass-card animate-scalein" style="padding: 1.25rem 0.5rem; text-align: center;">
                        <div style="font-size: 0.72rem; text-transform: uppercase; color: #A1A1AA; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 0.75rem;">Skills Radar Spectrum</div>
                        <svg width="200" height="200" viewBox="0 0 200 200" style="margin: 0 auto; display: block;">
                            <polygon points="100,35 165,100 100,165 35,100" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <polygon points="100,50 150,100 100,150 50,100" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <polygon points="100,65 135,100 100,135 65,100" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <polygon points="100,80 120,100 100,120 80,100" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <line x1="100" y1="35" x2="100" y2="165" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <line x1="35" y1="100" x2="165" y2="100" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                            <polygon points="{p1_x},{p1_y} {p2_x},{p2_y} {p3_x},{p3_y} {p4_x},{p4_y}" fill="rgba(139, 92, 246, 0.2)" stroke="#8B5CF6" stroke-width="1.5"/>
                            <circle cx="{p1_x}" cy="{p1_y}" r="3" fill="#8B5CF6"/>
                            <circle cx="{p2_x}" cy="{p2_y}" r="3" fill="#8B5CF6"/>
                            <circle cx="{p3_x}" cy="{p3_y}" r="3" fill="#8B5CF6"/>
                            <circle cx="{p4_x}" cy="{p4_y}" r="3" fill="#8B5CF6"/>
                            <text x="100" y="28" fill="#A1A1AA" font-size="7" text-anchor="middle" font-family="Inter" font-weight="600">Resume</text>
                            <text x="170" y="103" fill="#A1A1AA" font-size="7" text-anchor="start" font-family="Inter" font-weight="600">AI/ML</text>
                            <text x="100" y="177" fill="#A1A1AA" font-size="7" text-anchor="middle" font-family="Inter" font-weight="600">SE</text>
                            <text x="30" y="103" fill="#A1A1AA" font-size="7" text-anchor="end" font-family="Inter" font-weight="600">DSA</text>
                        </svg>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with col_dash_2:
                # Recruiter Assessment Summary
                st.markdown(
                    f"""
                    <div class="glass-card animate-fadeup" style="height: calc(100% - 1.5rem); border-left: 4px solid #8B5CF6 !important; line-height: 1.6; padding: 1.5rem !important;">
                        <div style="font-size: 0.75rem; text-transform: uppercase; color: #8B5CF6; font-weight: 700; letter-spacing: 0.75px; margin-bottom: 0.75rem;">📋 Recruiter Assessment Summary</div>
                        <div style="font-size: 0.95rem; color: #FAFAFA; line-height: 1.7;">{html.escape(report.summary)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            # 2. Category Scores Cards (Columns)
            st.markdown(
                """
                <div class="report-section-title" style="margin-top: 1.5rem;">
                    <span>📊 Category Performance Breakdown</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            cols = st.columns(4)
            for idx, cat_score in enumerate(report.category_scores):
                with cols[idx]:
                    val = cat_score.score
                    color = "#22C55E" if val >= 80 else ("#F59E0B" if val >= 60 else "#EF4444")
                    st.markdown(
                        f"""
                        <div class="glass-card card-perf" style="border-top: 3px solid {color} !important;">
                            <div style="font-size: 0.75rem; font-weight: 600; opacity: 0.8; height: 38px; overflow: hidden; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: center; color: #A1A1AA;">{html.escape(cat_score.category)}</div>
                            <div style="font-size: 1.8rem; font-weight: 700; color: {color};">{val:.1f}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            # 3. Strengths & Weaknesses Columns
            col_str, col_weak = st.columns(2)
            with col_str:
                st.markdown(
                    """
                    <div class="report-section-title" style="margin-top: 1rem;">
                        <span>🟢 Key Strengths</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                strengths_html = ""
                for strength in report.strengths:
                    strengths_html += f'<div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px; font-size: 0.9rem; color: #FAFAFA;"><span style="color: #22C55E;">✓</span><span>{html.escape(strength)}</span></div>'
                st.markdown(f'<div class="glass-card animate-fadeup">{strengths_html}</div>', unsafe_allow_html=True)
                
            with col_weak:
                st.markdown(
                    """
                    <div class="report-section-title" style="margin-top: 1rem;">
                        <span>🔴 Areas for Improvement</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                weaknesses_html = ""
                for weakness in report.weaknesses:
                    weaknesses_html += f'<div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px; font-size: 0.9rem; color: #FAFAFA;"><span style="color: #EF4444;">▲</span><span>{html.escape(weakness)}</span></div>'
                st.markdown(f'<div class="glass-card animate-fadeup">{weaknesses_html}</div>', unsafe_allow_html=True)
            
            # 4. Suggestions
            st.write("")
            st.markdown(
                """
                <div class="report-section-title" style="margin-top: 1rem;">
                    <span>🚀 Study & Preparation Suggestions</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            sug_html = ""
            for suggestion in report.suggestions:
                sug_html += f'<div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px; font-size: 0.9rem; color: #FAFAFA;"><span style="color: #8B5CF6;">&bull;</span><span>{html.escape(suggestion)}</span></div>'
            st.markdown(f'<div class="glass-card animate-fadeup">{sug_html}</div>', unsafe_allow_html=True)
            
            # 5. Detailed Q&A Expander
            st.write("---")
            with st.expander("🔍 View Detailed Question-by-Question Technical Feedback"):
                for i, qa in enumerate(session.history):
                    st.markdown(f"#### Question {i+1} ({qa.question.category} &middot; {qa.question.topic})")
                    st.markdown(f"**Q:** {qa.question.text}")
                    st.markdown(f"**A:** *{qa.user_answer}*")
                    
                    if qa.evaluation:
                        e = qa.evaluation
                        q_color = "#22C55E" if e.score >= 4 else ("#F59E0B" if e.score >= 3 else "#EF4444")
                        st.markdown(
                            f"""
                            <div style="padding:1.25rem; border-radius:12px; background-color:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.05); border-left: 4px solid {q_color} !important; margin-top:0.5rem; margin-bottom:1.5rem;">
                                <strong>Technical Score:</strong> <span style="color:{q_color}; font-weight:700;">{e.score}/5</span><br><br>
                                <strong>Accuracy:</strong> {html.escape(e.accuracy_feedback)}<br>
                                <strong>Depth:</strong> {html.escape(e.depth_feedback)}<br>
                                <strong>Clarity:</strong> {html.escape(e.clarity_feedback)}<br>
                                <strong>Completeness:</strong> {html.escape(e.completeness_feedback)}<br><br>
                                <strong>Key Strengths:</strong> {html.escape(', '.join(e.strengths)) if e.strengths else 'None'}<br>
                                <strong>Key Gaps:</strong> {html.escape(', '.join(e.weaknesses)) if e.weaknesses else 'None'}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.warning("No evaluation could be compiled for this question due to an API timeout.")
            
            st.write("")
            if st.button("Return to Upload Hub 🏠", use_container_width=True):
                st.session_state["interview_session"] = None
                st.session_state["candidate_profile"] = None
                st.rerun()

    else:
        # ---------------------------------------------------------
        # VIEW B: Active Interview Screen
        # ---------------------------------------------------------
        st.markdown(
            """
            <div style="margin-bottom: 1.5rem;">
                <h2 style="font-size: 1.5rem; font-weight: 600; color: #FAFAFA; margin: 0; display: flex; align-items: center; gap: 8px;">
                    💬 Technical Interview Room
                </h2>
                <p style="font-size: 0.85rem; color: #A1A1AA; margin: 4px 0 0 0;">Respond to the AI-generated questions based on your background.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Progress bar and stats
        progress_val = min(session.current_question_index / DEFAULT_QUESTION_COUNT, 1.0)
        st.progress(progress_val)
        
        current_q = session.questions[session.current_question_index]
        
        # Display conversation history
        for qa in session.history:
            with st.chat_message("assistant"):
                st.markdown(
                    f"""<div style="font-family: 'Inter', sans-serif;">
<span style="font-size: 0.72rem; text-transform: uppercase; color: #A855F7; font-weight: 700; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">{html.escape(qa.question.category)}</span>
<div style="font-size: 0.95rem; color: #FAFAFA; line-height: 1.5;">{html.escape(qa.question.text)}</div>
</div>""", 
                    unsafe_allow_html=True
                )
            with st.chat_message("user"):
                st.markdown(
                    f"""<div style="font-family: 'Inter', sans-serif; font-size: 0.95rem; color: #FAFAFA; line-height: 1.5;">
{html.escape(qa.user_answer)}
</div>""",
                    unsafe_allow_html=True
                )
        
        # Display current question with rich UI
        state = st.session_state.get("interview_state")
        difficulty = state.current_difficulty if state else "Medium"
        difficulty_color = (
            "#22C55E" if difficulty == "Easy" 
            else ("#F59E0B" if difficulty == "Medium" 
                  else ("#EF4444" if difficulty == "Hard" else "#A855F7"))
        )
        rgba_color = (
            "34, 197, 94" if difficulty == "Easy"
            else ("245, 158, 11" if difficulty == "Medium"
                  else ("239, 68, 68" if difficulty == "Hard" else "168, 85, 247"))
        )
        est_time = (
            "2-3 min" if difficulty == "Easy" 
            else ("3-4 min" if difficulty == "Medium" 
                  else ("4-5 min" if difficulty == "Hard" else "5-6 min"))
        )
        
        # Animated AI Avatar SVG
        ai_icon_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12A10 10 0 0 1 12 2z"/><path d="M12 6v6l4 2"/></svg>'

        with st.chat_message("assistant"):
            st.markdown(
                f"""<div class="question-box animate-scalein">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
<div class="ai-avatar-badge">
{ai_icon_svg}
<span>Interview AI</span>
</div>
<div style="display: flex; gap: 8px;">
<span class="meta-badge" style="color: {difficulty_color}; border-color: rgba({rgba_color}, 0.25); background: rgba({rgba_color}, 0.05);">{difficulty}</span>
<span class="meta-badge">⏱️ {est_time}</span>
</div>
</div>
<div style="font-size: 0.75rem; text-transform: uppercase; color: #A855F7; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 0.5rem;">{html.escape(current_q.category)} &middot; {html.escape(current_q.topic)}</div>
<div class="question-text" style="font-size: 1.1rem; font-weight: 500; color: #FAFAFA; line-height: 1.5; margin-bottom: 1rem;">{html.escape(current_q.text)}</div>
<div style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: #A1A1AA;">
<div class="typing-dots">
<div class="typing-dot"></div>
<div class="typing-dot"></div>
<div class="typing-dot"></div>
</div>
<span>Interview AI is listening...</span>
</div>
</div>""",
                unsafe_allow_html=True
            )

        # Input form for candidate answer
        with st.form(key="answer_form", clear_on_submit=True):
            user_ans = st.text_area(
                "Your Response:", 
                placeholder="Provide your technical explanation here...",
                height=150
            )
            
            # Client-side live word and character counters
            st.markdown(
                """
                <div id="counter-container" style="display: flex; justify-content: flex-end; gap: 16px; font-size: 0.8rem; color: #A1A1AA; margin-top: -10px; margin-bottom: 12px; font-family: 'Inter', sans-serif;">
                    <span>Words: <strong id="word-count" style="color: #8B5CF6;">0</strong></span>
                    <span>Characters: <strong id="char-count" style="color: #8B5CF6;">0</strong></span>
                </div>
                <script>
                    (function() {
                        const runCounter = () => {
                            const textarea = document.querySelector('textarea[data-testid="stTextArea"]');
                            if (!textarea) return false;
                            
                            const update = () => {
                                const text = textarea.value || '';
                                const chars = text.length;
                                const words = text.trim() === '' ? 0 : text.trim().split(/\\s+/).length;
                                const wordEl = document.getElementById('word-count');
                                const charEl = document.getElementById('char-count');
                                if (wordEl) wordEl.innerText = words;
                                if (charEl) charEl.innerText = chars;
                            };
                            
                            textarea.removeEventListener('input', update);
                            textarea.addEventListener('input', update);
                            update();
                            return true;
                        };
                        
                        let attempts = 0;
                        const interval = setInterval(() => {
                            attempts++;
                            if (runCounter() || attempts > 20) {
                                clearInterval(interval);
                            }
                        }, 250);
                    })();
                </script>
                """,
                unsafe_allow_html=True
            )
            
            col_btn_1, col_btn_2 = st.columns([3, 1])
            
            with col_btn_1:
                submit_button = st.form_submit_button("Submit Answer ➔", use_container_width=True)
            with col_btn_2:
                skip_button = st.form_submit_button("Skip / I don't know", use_container_width=True)
            
            if submit_button:
                if not user_ans.strip():
                    st.warning("Please type a valid response before submitting.")
                else:
                    with st.spinner("Recording answer..."):
                        try:
                            InterviewEngine.submit_answer(session, user_ans)
                            st.session_state["interview_session"] = session
                            st.rerun()
                        except InterviewEngineError as e:
                            st.error("Failed to submit answer. Please try again.")
                            
            if skip_button:
                with st.spinner("Recording skipped status..."):
                    try:
                        InterviewEngine.submit_answer(session, "I don't know / skipped.")
                        st.session_state["interview_session"] = session
                        st.rerun()
                    except InterviewEngineError as e:
                        st.error("Failed to skip question. Please try again.")
