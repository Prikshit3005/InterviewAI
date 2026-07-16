<div align="center">

# 🎯 InterviewAI

### AI-Powered Adaptive Technical Interview Simulator

*Generate personalized interviews from a resume, dynamically adapt question difficulty based on candidate performance, evaluate responses using Gemini AI, and produce recruiter-style performance reports.*

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge)
![AI](https://img.shields.io/badge/LLM-Adaptive%20Interview-blueviolet?style=for-the-badge)

---

### 🚀 Upload Resume → AI Interview → Adaptive Difficulty → Detailed Report

</div>

---

# 📖 Overview

InterviewAI is an intelligent technical interview simulator that behaves like a real interviewer rather than a fixed questionnaire.

Unlike traditional resume parsers that simply extract skills and ask predefined questions, InterviewAI continuously evaluates candidate performance and automatically adjusts the difficulty of upcoming questions.

The entire interview is personalized using the candidate's resume, creating a realistic recruiter-style interview experience.

---

# ✨ Features

## 📄 AI Resume Parsing

- Extracts text from uploaded PDF resumes
- Identifies:
  - Education
  - Skills
  - Projects
  - Experience
  - Technologies
- Builds a structured candidate profile using Gemini AI

---

## 🎯 Personalized Interview Generation

Instead of asking generic DSA questions, InterviewAI creates questions based on:

- Resume projects
- Programming languages
- Frameworks
- Technical skills
- Academic background

Each interview is unique.

---

## 🧠 Adaptive Interview Engine

This is the core feature of the project.

After every answer, the AI evaluates the candidate and adjusts the next question difficulty.

Example progression:

```
Easy
   ↓
Medium
   ↓
Hard
   ↓
Expert
```

or

```
Hard
 ↓
Medium
 ↓
Easy
```

depending on candidate performance.

Unlike fixed interview bots, InterviewAI continuously adapts throughout the session.

---

## 🤖 AI Answer Evaluation

Every answer is evaluated using Gemini.

The AI considers:

- Technical correctness
- Completeness
- Problem-solving ability
- Communication clarity
- Confidence
- Practical understanding

Instead of simply marking answers as right or wrong.

---

## 📊 Recruiter Style Report

After completing the interview, InterviewAI generates:

- Overall score
- Category-wise scores
- Technical strengths
- Weaknesses
- Improvement suggestions
- Hiring recommendation

Exactly how many recruiters summarize interviews internally.

---

## ⚡ Development Mode

To avoid Gemini API quota limitations during development, InterviewAI includes an offline Development Mode.

Features:

- Cached interview sessions
- Offline interview playback
- Zero API calls
- Rapid UI development
- Deterministic testing

This dramatically reduces API usage while allowing full frontend testing.

---

# 🏗️ System Architecture

```
                   Resume PDF
                        │
                        ▼
             Resume Text Extraction
                        │
                        ▼
          Gemini Profile Structuring
                        │
                        ▼
            Candidate Profile Object
                        │
                        ▼
        Personalized Question Generator
                        │
                        ▼
         Technical Interview Session
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
Candidate Answer             Gemini Evaluation
        │                               │
        └───────────────┬───────────────┘
                        ▼
          Adaptive Difficulty Engine
                        │
                        ▼
              Next Question Selection
                        │
                        ▼
               Final Performance Report
```

---

# 🧩 Project Structure

```
InterviewAI
│
├── app.py
├── config
│
├── src
│   ├── models
│   ├── services
│   ├── utils
│
├── data
│
├── requirements.txt
│
└── README.md
```

---

# 🧠 Adaptive Difficulty Logic

The interview is not static.

After every answer:

```
Candidate Answer
        │
        ▼
AI Evaluation
        │
        ▼
Performance Score
        │
        ▼
Difficulty Adjustment
        │
        ▼
Generate Next Question
```

Example:

```
Q1 Easy
        Score 90%
            ↓
Q2 Medium
        Score 85%
            ↓
Q3 Hard
        Score 45%
            ↓
Q4 Medium
        Score 80%
            ↓
Q5 Hard
```

This creates a much more realistic interview experience.

---

# 📈 Interview Flow

```
Upload Resume

      ↓

Resume Parsing

      ↓

Profile Generation

      ↓

Generate Personalized Questions

      ↓

Interview Begins

      ↓

Answer Evaluation

      ↓

Adaptive Difficulty

      ↓

Repeat

      ↓

Performance Report
```

---

# 💻 Tech Stack

### Frontend

- Streamlit

### Backend

- Python

### AI

- Google Gemini API

### Data Validation

- Pydantic

### Resume Parsing

- PDF Processing

### Development

- Git
- GitHub

---

# 📷 Screenshots

## Resume Upload

> *(Add Screenshot Here)*

---

## Candidate Profile

> *(Add Screenshot Here)*

---

## Technical Interview

> *(Add Screenshot Here)*

---

## Adaptive Difficulty

> *(Add Screenshot Here)*

---

## Final Evaluation Report

> *(Add Screenshot Here)*

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/Prikshit3005/InterviewAI.git
```

Go into the directory

```bash
cd InterviewAI
```

Create virtual environment

```bash
python -m venv venv
```

Activate environment

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create `.env`

```
GEMINI_API_KEY=YOUR_API_KEY
DEV_MODE=False
```

Run

```bash
streamlit run app.py
```

---

# 🔧 Development Mode

Enable offline mode by changing:

```
DEV_MODE=True
```

Development mode:

- Uses cached interview sessions
- Skips Gemini API calls
- Allows unlimited frontend testing
- Perfect for UI development without consuming API quota

---

# 🎯 Future Improvements

- Voice Interview Mode
- Webcam & Emotion Analysis
- Coding Round
- HR Interview Round
- Company-specific Interviews
- Resume ATS Score
- Interview History Dashboard
- Authentication
- Cloud Deployment

---

# 🌟 Why InterviewAI?

Unlike conventional interview bots, InterviewAI introduces adaptive interviewing.

Instead of following a fixed question list, it continuously evaluates the candidate and modifies the interview based on live performance.

This creates a much more realistic recruiter-like experience while also reducing development costs through an intelligent offline testing mode.

---

# 👨‍💻 Author

**Prikshit Sharma**

B.E. Electronics & Computer Science  
Thapar Institute of Engineering and Technology

GitHub

https://github.com/Prikshit3005

---

# ⭐ If you found this project interesting

Please consider giving it a ⭐ on GitHub!
