import streamlit as st
import json
import subprocess
from pathlib import Path
import pandas as pd

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True, parents=True)
BACKEND_SCRIPT = "main.py"  # Adjust if your script is named differently

st.set_page_config(page_title="Qualitative Analysis Dashboard", layout="wide")

st.title("Qualitative Thematic Analysis Dashboard")

# --- Sidebar: Upload new data and run analysis ---
st.sidebar.header("Start New Analysis")
uploaded_excel = st.sidebar.file_uploader("Upload Interview Excel (.xlsx)", type=["xlsx"])
uploaded_background = st.sidebar.file_uploader("Upload Project Background (.txt)", type=["txt"])
run_analysis = st.sidebar.button("Run Analysis")

if run_analysis and uploaded_excel and uploaded_background:
    excel_path = OUTPUTS_DIR / "uploaded_data.xlsx"
    background_path = OUTPUTS_DIR / "uploaded_background.txt"
    with open(excel_path, "wb") as f:
        f.write(uploaded_excel.read())
    with open(background_path, "wb") as f:
        f.write(uploaded_background.read())
    st.sidebar.info("Files uploaded. Running analysis...")

    # Run the backend analysis script
    try:
        result = subprocess.run(
            [
                "python", BACKEND_SCRIPT,
                str(excel_path),
                "--background", str(background_path)
            ],
            capture_output=True,
            text=True,
            cwd="."
        )
        if result.returncode == 0:
            st.sidebar.success("Analysis complete!")
        else:
            st.sidebar.error(f"Analysis failed:\n{result.stderr}")
    except Exception as e:
        st.sidebar.error(f"Error running analysis: {e}")

# --- Main: Browse existing analyses ---
st.header("Browse Analyses")

all_analyses_path = OUTPUTS_DIR / "all_analyses.json"
if all_analyses_path.exists():
    with open(all_analyses_path) as f:
        all_analyses = json.load(f)
    question_names = list(all_analyses.keys())
    selected_question = st.selectbox("Select a question", question_names)
    analysis = all_analyses[selected_question]

    st.subheader(f"Question: {selected_question}")
    st.markdown(f"**Headline:** {analysis['headline']}")
    st.markdown(f"**Summary:** {analysis['summary']}")

    # --- Download buttons for per-question outputs ---
    col1, col2 = st.columns(2)
    # Per-question JSON
    per_question_json_path = OUTPUTS_DIR / f"analysis_{selected_question}.json"
    if per_question_json_path.exists():
        with open(per_question_json_path, "r") as f:
            per_question_json = f.read()
        col1.download_button(
            label=f"Download analysis_{selected_question}.json",
            data=per_question_json,
            file_name=f"analysis_{selected_question}.json",
            mime="application/json"
        )
    # Per-question Excel (classifications)
    per_question_xlsx_path = OUTPUTS_DIR / f"classifications_{selected_question}.xlsx"
    if per_question_xlsx_path.exists():
        with open(per_question_xlsx_path, "rb") as f:
            per_question_xlsx = f.read()
        col2.download_button(
            label=f"Download classifications_{selected_question}.xlsx",
            data=per_question_xlsx,
            file_name=f"classifications_{selected_question}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- Show themes and quotes as before ---
    for theme in analysis["themes"]:
        st.markdown(f"### {theme['title']} ({theme['participant_count']} participants)")
        st.markdown(theme["description"])
        st.markdown("**Quotes:**")
        for q in theme["quotes"]:
            st.markdown(f"> {q['quote']}  \n<span style='color:gray'>({q['participant_id']})</span>", unsafe_allow_html=True)
        st.markdown("---")

    # --- Show full response-to-theme classification table ---
    if per_question_xlsx_path.exists():
        df = pd.read_excel(per_question_xlsx_path)
        st.markdown("#### Full Response-to-Theme Classification Table")
        st.dataframe(df, use_container_width=True)

    st.download_button(
        label="Download all_analyses.json",
        data=json.dumps(all_analyses, indent=2),
        file_name="all_analyses.json",
        mime="application/json"
    )
else:
    st.warning("No analysis found. Please run your backend analysis pipeline first.")

# --- Optionally: Show low-effort flags ---
low_effort_path = OUTPUTS_DIR / "low_effort_flags.json"
if low_effort_path.exists():
    with open(low_effort_path) as f:
        low_effort = json.load(f)
    st.sidebar.header("Low-Effort Flags")
    for q, ids in low_effort.items():
        if ids:
            st.sidebar.markdown(f"**{q}:** {', '.join(ids)}")
        else:
            st.sidebar.markdown(f"**{q}:** _None_")