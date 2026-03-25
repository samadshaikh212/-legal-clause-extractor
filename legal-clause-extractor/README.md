# Legal Clause Extractor ⚖️

An AI-powered web app that analyzes contract PDFs and automatically extracts obligations, rights, deadlines, and risk scores — in seconds.

Built with **Streamlit + Google Gemini 1.5 Flash + PyMuPDF**.

---

## What it does

- Upload any contract PDF
- AI reads every paragraph and classifies it as: Obligation, Right, Deadline, Payment, Termination, Confidentiality, Liability, Indemnity, or Governing Law
- Assigns a risk score (High / Medium / Low) with a reason
- Generates a plain-English executive summary
- Filter by clause type or risk level
- Export results as CSV

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| PDF parsing | PyMuPDF (fitz) |
| AI / NLP | Google Gemini 1.5 Flash |
| Deployment | Streamlit Cloud (free) |

## Project Structure

```
legal-clause-extractor/
├── app.py              # Main Streamlit UI
├── extractor.py        # Gemini API clause analysis
├── utils.py            # PDF reading + text chunking
├── requirements.txt    # Dependencies
└── README.md
```

## Local Setup

```bash
git clone https://github.com/yourusername/legal-clause-extractor
cd legal-clause-extractor
pip install -r requirements.txt
streamlit run app.py
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com).

## Deploy on Streamlit Cloud (free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `app.py` as the entry point
5. Done — live URL in 2 minutes

## Resume Description

> Built a full-stack NLP application using Google Gemini 1.5 Flash to automatically extract and classify legal clauses (obligations, rights, liabilities) from contract PDFs. Implemented PDF parsing pipeline with PyMuPDF, structured prompt engineering for JSON output, and risk scoring. Deployed as a free web app on Streamlit Cloud.

---

Made for academic project — Semester VI, ML coursework.
