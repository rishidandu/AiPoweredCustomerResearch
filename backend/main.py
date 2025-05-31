import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import StrOutputParser
from concurrent.futures import ThreadPoolExecutor
import re

# ---------------------------------------------------------------------------
# 1. CONFIGURATION -----------------------------------------------------------
# ---------------------------------------------------------------------------

load_dotenv()

@dataclass
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", 0))
    max_quotes_per_theme: int = int(os.getenv("MAX_QUOTES_PER_THEME", 3))
    max_workers: int = int(os.getenv("MAX_WORKERS", 8))
    out_dir: Path = Path(os.getenv("OUT_DIR", "outputs"))
    project_background: str = os.getenv("PROJECT_BACKGROUND", "")

settings = Settings()
settings.out_dir.mkdir(exist_ok=True, parents=True)

# ---------------------------------------------------------------------------
# 2. HELPER FUNCTIONS --------------------------------------------------------
# ---------------------------------------------------------------------------

def read_interview_data(file_path: Path) -> Dict[str, List[Dict[str, str]]]:
    """Return a dict: {question: [{participant_id, response}, ...]}"""
    df = pd.read_excel(file_path)
    question_columns = df.columns[1:7]  # columns B‑G
    data: Dict[str, List[Dict[str, str]]] = {}
    for col in question_columns:
        responses = (
            df[[df.columns[0], col]]
            .dropna()
            .rename(columns={df.columns[0]: "ID", col: "response"})
        )
        data[col] = [
            {"participant_id": str(row["ID"]), "response": str(row["response"])}
            for _, row in responses.iterrows()
        ]
    return data


def build_llm() -> ChatOpenAI:
    if settings.provider == "openai":
        return ChatOpenAI(model_name=settings.model, temperature=settings.temperature)
    raise ValueError(f"Unsupported provider: {settings.provider}")


def create_prompt(max_quotes: int) -> PromptTemplate:
    """Prompt template with project background included."""
    template = f"""
{{project_background}}

You are a senior qualitative researcher. Produce a thematic analysis **only** in JSON.

Guidelines:
- 3‑5 themes, mutually exclusive & collectively exhaustive.
- Each theme: ≤ {max_quotes} representative quotes, each from a **different** participant.
- Never reuse quotes across themes.
- Keep language crisp; avoid stock phrases.

JSON schema:
{{{{"headline": str,
"summary": str,
"themes": [
    {{{{"title": str,
    "description": str,
    "participant_count": int,
    "quotes": [{{{{"participant_id": str, "quote": str}}}}]
    }}}}
  ]
}}}}

Question: {{question_text}}
Participants: {{num_participants}}
Responses:
{{responses}}

Respond **only** with valid JSON — no commentary.
"""
    return PromptTemplate(
        input_variables=["project_background", "question_text", "num_participants", "responses"],
        template=template.strip(),
    )


def validate_analysis(question: str, analysis: Dict[str, Any]):
    """Ensure no quote/participant duplication across or within themes."""
    seen_quotes = set()
    for theme in analysis.get("themes", []):
        pids = set()
        for q in theme.get("quotes", []):
            quote = q["quote"].strip()
            pid = q["participant_id"]
            if quote in seen_quotes:
                raise ValueError(f"Quote reused across themes in {question}: {quote[:60]}")
            if pid in pids:
                raise ValueError(f"Duplicate participant {pid} within theme '{theme['title']}'")
            seen_quotes.add(quote)
            pids.add(pid)


def save_classification_sheet(question: str, analysis: Dict[str, Any]):
    rows = []
    for theme in analysis.get("themes", []):
        for q in theme.get("quotes", []):
            rows.append({
                "question": question,
                "theme": theme["title"],
                "participant_id": q["participant_id"],
                "quote": q["quote"],
            })
    if rows:
        df = pd.DataFrame(rows)
        df.to_excel(settings.out_dir / f"classifications_{question}.xlsx", index=False)

# ---------------------------------------------------------------------------
# 3. MAIN ANALYSIS -----------------------------------------------------------
# ---------------------------------------------------------------------------

def analyse_question(llm_chain: Runnable, question: str, responses: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    # Use all responses for full analysis
    formatted = "\n".join([f"P{r['participant_id']}: {r['response']}" for r in responses])
    result = llm_chain.invoke({
        "question_text": question,
        "num_participants": len(responses),
        "responses": formatted,
    })
    if hasattr(result, "content"):
        result = result.content
    if not result or not result.strip():
        print(f"[DEBUG] LLM output for {question} is empty or whitespace.")
    # Remove Markdown code block if present
    if result.strip().startswith("```"):
        result = re.sub(r"^```[a-zA-Z]*\n?", "", result.strip())
        result = re.sub(r"```$", "", result.strip())
    try:
        analysis = json.loads(result)
        validate_analysis(question, analysis)
        return analysis
    except (json.JSONDecodeError, ValueError) as err:
        print(f"[WARN] {question}: {err}")
        print(f"[DEBUG] Raw LLM output for {question}:\n{result}\n{'-'*60}")
        return None

# ---------------------------------------------------------------------------
# 4. DRIVER WITH CONCURRENCY -------------------------------------------------
# ---------------------------------------------------------------------------

def run_all_questions(questions: Dict[str, List[Dict[str, str]]]):
    prompt = create_prompt(settings.max_quotes_per_theme)
    llm = build_llm()
    # Pre‑fill project background once to shrink payload
    chain: Runnable = prompt.partial(project_background=settings.project_background) | llm | StrOutputParser()

    results: Dict[str, Dict] = {}
    with ThreadPoolExecutor(max_workers=settings.max_workers) as pool:
        futures = {
            pool.submit(analyse_question, chain, q, r): q for q, r in questions.items()
        }
        for fut in futures:
            qname = futures[fut]
            res = fut.result()
            if res:
                results[qname] = res
                (settings.out_dir / f"analysis_{qname}.json").write_text(json.dumps(res, indent=2))
                save_classification_sheet(qname, res)
    (settings.out_dir / "all_analyses.json").write_text(json.dumps(results, indent=2))

# ---------------------------------------------------------------------------
# 5. LOW‑EFFORT FLAGGER ------------------------------------------------------
# ---------------------------------------------------------------------------

def low_effort(responses: List[Dict[str, str]], short_thresh: int = 6):
    flagged = []
    for r in responses:
        txt = r["response"].strip()
        unique = len(set(txt.lower().split()))
        if len(txt.split()) < short_thresh or unique <= 2:
            flagged.append(r["participant_id"])
    return flagged

# ---------------------------------------------------------------------------
# 6. CLI ENTRY ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser("Thematic analysis pipeline")
    parser.add_argument("excel", type=Path, help="Path to interview .xlsx file")
    parser.add_argument("--background", type=Path, help="Text file with project background")
    args = parser.parse_args()

    if args.background and args.background.exists():
        settings.project_background = args.background.read_text().strip()

    data = read_interview_data(args.excel)

    # Optional lazy‑answer scan
    lazy = {q: low_effort(r) for q, r in data.items()}
    (settings.out_dir / "low_effort_flags.json").write_text(json.dumps(lazy, indent=2))

    run_all_questions(data)
    print(f"Done. Outputs in {settings.out_dir.resolve()}")


if __name__ == "__main__":
    main()