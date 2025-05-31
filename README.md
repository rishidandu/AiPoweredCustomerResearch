# Qualitative Thematic Analysis Platform

## Overview
This project provides an end-to-end pipeline for qualitative thematic analysis of interview data, with a modern LLM-powered backend and an interactive Streamlit dashboard frontend. It is designed for analyzing responses to open-ended questions (e.g., from Excel files), extracting themes, and presenting results in a user-friendly way.

---

## Directory Structure
```
backend/
  main.py                # Backend analysis pipeline
  streamlit_app.py       # Streamlit dashboard app
  project_background.txt # Editable project background
  outputs/               # All analysis outputs (JSON, Excel, etc.)
  requirements.txt       # Python dependencies
```
---

## Setup
1. **Clone the repository and navigate to the project directory.**
2. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   pip install streamlit
   ```
3. **(Optional) Set up your OpenAI API key:**
   - Add your key to a `.env` file in `backend/` as `OPENAI_API_KEY=sk-...`

---

## Running the Backend Analysis Script
You can run the backend analysis pipeline directly from the command line:

```bash
cd backend
python main.py usercue_interview_case_study_6Qs.xlsx --background project_background.txt
```
- Replace `usercue_interview_case_study_6Qs.xlsx` with your Excel file.
- The script will output results to the `outputs/` directory, including `all_analyses.json` and per-question files.

---

## Using the Streamlit Dashboard
1. **Start the app:**
   ```bash
   cd backend
   streamlit run streamlit_app.py
   ```
2. **Features:**
   - Upload a new Excel file and project background.
   - Click "Run Analysis" to trigger the backend pipeline.
   - Browse and download analysis results interactively.
   - View low-effort response flags in the sidebar.

---

## Key Functions in `main.py`
- `read_interview_data(file_path)`: Reads the Excel file and extracts all question columns and responses.
- `create_prompt(max_quotes)`: Builds the LLM prompt template for thematic analysis.
- `analyse_question(llm_chain, question, responses)`: Runs the LLM pipeline for a single question and parses the output.
- `run_all_questions(questions)`: Runs the analysis for all questions concurrently and saves outputs.
- `low_effort(responses)`: Flags short or repetitive responses as "low effort".
- `main()`: CLI entrypoint; parses arguments, loads data, runs analysis, and saves results.

---

## Customization
- **Edit `project_background.txt`** to update the project context for your analyses.
- **Add or remove questions** by changing the columns in your Excel file.
- **Tune concurrency, model, or output location** by editing the `Settings` dataclass in `main.py`.

---

## Support
If you have questions or need help, open an issue or contact the project maintainer. 