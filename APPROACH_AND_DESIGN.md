# Approach, Design Decisions, and Production Considerations

## Overview
This document explains the rationale, design choices, and tradeoffs made in building the Qualitative Thematic Analysis Platform. It also outlines how the approach might evolve for a production-grade deployment.

---

## Approach
- **Goal:** Automate and standardize thematic analysis of qualitative interview data using LLMs, ensuring accuracy, transparency, and reusability.
- **Pipeline:**
  1. Ingest Excel data (multiple open-ended questions, many participants)
  2. For each question, prompt an LLM to generate a concise thematic analysis (headline, summary, themes, representative quotes)
  3. Output results in structured JSON and Excel for review and downstream use
  4. Provide a Streamlit dashboard for interactive exploration and re-analysis

---

## Key Design Decisions

### 1. **Prompt Engineering**
- **Explicit JSON schema:** Ensures outputs are machine-readable and consistent.
- **Strict instructions:** Prevents LLM tropes, hallucinations, and misattribution.
- **Representative quotes only:** Focuses on clarity and brevity, not exhaustive classification.

### 2. **Reusability**
- **Project background as parameter/file:** Enables use across projects and domains.
- **Automatic question detection:** Handles any number of questions without code changes.

### 3. **Concurrency**
- **ThreadPoolExecutor:** Analyzes all questions in parallel, reducing total runtime.

### 4. **Inspectability**
- **Per-question Excel files:** Allow manual review of theme assignments and quotes.
- **Low-effort flagging:** Flags short or repetitive responses for quality control.

### 5. **Frontend**
- **Streamlit app:** Enables non-technical users to upload data, run analysis, and explore results interactively.

---

## Assumptions
- Input Excel files are well-structured: first column is participant ID, subsequent columns are open-ended questions.
- Project background is provided as a text file or string.
- LLM (e.g., OpenAI GPT-4o) is available and API keys are configured.
- Users want representative, not exhaustive, quote classification by default.

---

## Tradeoffs & Considerations

### 1. **LLM Output Reliability**
- **Tradeoff:** LLMs can hallucinate or misattribute quotes despite prompt engineering.
- **Mitigation:** Strict prompt, post-processing validation, and manual review outputs.
- **Alternative:** For production, consider a two-step process: (1) extract themes, (2) classify every response.

### 2. **Scalability**
- **Current:** Thread pool concurrency is sufficient for dozens of questions; for hundreds/thousands, consider async or distributed processing.
- **Production:** Add rate limiting, batching, and error retries for large-scale use.

### 3. **Exhaustiveness vs. Clarity**
- **Current:** For full auditability, add an option to classify every response.
- **Alternative:** Only top quotes per theme are classified for clarity and reviewability.

### 4. **Frontend Simplicity**
- **Current:** Streamlit is fast to build and easy for users, but not as customizable as a full web app.
- **Production:** Consider React or Dash for more complex workflows, user authentication, or multi-user support.

### 5. **Security & Privacy**
- **Current:** Assumes data is not sensitive or is handled in a secure environment.
- **Production:** Add authentication, access controls, and data encryption as needed.

---

## What Would Change in Production
- **Robust error handling:** More granular retries, logging, and alerting.
- **LLM output validation:** Automated checks to ensure all quotes are present in the input, no hallucinations, and correct attributions.
- **Full response classification:** Option to assign every response to a theme for compliance/audit needs.
- **Scalable backend:** Use async workers, queues, or cloud functions for large datasets.
- **User management:** Authentication, permissions, and audit logs.
- **UI/UX:** More advanced dashboard, filtering, and export options.
- **Testing:** Automated tests for data integrity, prompt effectiveness, and output validation.

---

## OPTIONAL BONUS POINTS

### 1. **Scalability to n=1000 or n=10000 participants**
- **Approach:**
  - Chunk responses for each question so that each LLM call stays within context limits (e.g., 100-200 responses per chunk).
  - Analyze each chunk independently, then merge/aggregate themes and re-run a summarization step if needed.
  - Use async workers or distributed processing (e.g., Celery, Ray) to parallelize across many questions and chunks.
  - Monitor and respect API rate limits; implement exponential backoff and retries.

### 2. **Scalability to 1000 questions**
- **Approach:**
  - The pipeline already supports any number of questions; for 1000+, use a distributed task queue (e.g., Celery, AWS Batch) to process questions in parallel.
  - Store intermediate and final outputs in a database or cloud storage for reliability.
  - Provide progress tracking and error reporting in the frontend.

### 3. **Evals Mechanism**
- **Approach:**
  - Build a test suite of gold-standard analyses (human-coded themes and quotes).
  - After each run, compare LLM outputs to gold standards using metrics like theme overlap, quote accuracy, and attribution correctness.
  - Visualize eval results in the dashboard; flag low-performing questions for manual review.

#### **Automatic Prompt Optimization**
- **Approach:**
  - Use eval metrics as feedback to a prompt optimization loop (e.g., grid search over prompt variants, or reinforcement learning with human feedback).
  - Automate prompt tweaks and re-run evals, selecting the prompt with the best performance.

### 4. **Detecting Low-Effort or LLM-Generated Answers**
- **Approach:**
  - Expand the low-effort flagger to include:
    - Response length, lexical diversity, and repetition metrics
    - Perplexity or burstiness (using a smaller language model)
    - LLM-generated text detectors (e.g., OpenAI's or GPTZero)
  - Flag suspicious responses for manual review in the dashboard.

### 5. **User Customization of LLM Provider, Model, and Prompt**
- **Approach:**
  - Expose provider/model/prompt settings in the Streamlit UI (dropdowns, text boxes).
  - Pass user selections to the backend pipeline via API or CLI args.
  - Dynamically construct the LLM and prompt objects based on user input.
  - Store user settings for reproducibility and auditability.

---

## Conclusion
This implementation balances speed, accuracy, and usability for research and prototyping. For production, focus would shift to robustness, scalability, and compliance, with more advanced validation and user management features. 
