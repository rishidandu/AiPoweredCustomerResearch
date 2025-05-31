from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os
import pandas as pd
from typing import List, Dict
import json
from concurrent.futures import ThreadPoolExecutor
import time

# Load environment variables from .env file
load_dotenv()

PROJECT_BACKGROUND = """The primary goal of this research study is to understand the consumer privacy market, specifically in the areas of network privacy (VPNs) and data deletion services. We aim to size the market, identify key customer needs and use cases, and validate product-market fit for CLIENT's offerings in these spaces. The insights from this study will inform CLIENT's go-to-market strategy and product roadmap to best address the needs of the target market.

Learning Objectives:
1. Understand the size and segmentation of the consumer privacy market
2. Identify key use cases, pain points, and unmet needs
3. Assess willingness to pay and preferred pricing models"""

def read_interview_data(file_path: str) -> Dict[str, List[Dict]]:
    """Read and process the Excel file containing interview responses."""
    df = pd.read_excel(file_path)
    print("DEBUG: DataFrame columns:", df.columns.tolist())
    
    # Get question columns (B through G)
    question_columns = df.columns[1:7]
    
    # Process each question
    questions_data = {}
    for col in question_columns:
        # Filter out empty responses
        responses = df[['ID', col]].dropna()
        
        # Convert to list of dicts with participant ID and response
        responses_list = [
            {"participant_id": str(row['ID']), "response": str(row[col])}
            for _, row in responses.iterrows()
        ]
        
        questions_data[col] = responses_list
    
    return questions_data

def create_analysis_pipeline():
    """Create the LLM analysis pipeline."""
    template = """
{project_background}

You are an expert qualitative researcher analyzing interview responses. Your task is to provide a thematic analysis of the following question and responses.

Question: {question_text}
Number of participants: {num_participants}

Responses:
{responses}

Please provide a thematic analysis in the following JSON format:
{{
    "headline": "A concise, engaging headline that answers the question (<20 words)",
    "summary": "1-2 sentence summary of the analysis",
    "themes": [
        {{
            "title": "Theme title that directly answers the question",
            "description": "Theme description",
            "participant_count": number of participants in this theme,
            "quotes": [
                {{
                    "participant_id": "participant ID",
                    "quote": "verbatim quote"
                }}
            ]
        }}
    ]
}}

Guidelines:
1. Themes should be "sufficient and necessary" and meaningfully capture the narrative
2. Aim for 3-5 themes per question
3. Each theme should have 3 representative quotes
4. Don't use the same quote for multiple themes
5. Don't use multiple quotes from the same participant in a theme
6. Quotes must be verbatim and accurately attributed
7. The analysis should not feel like it was written by an LLM

Respond ONLY with valid JSON, no commentary or markdown.
"""

    prompt = PromptTemplate(
        input_variables=["project_background", "question_text", "num_participants", "responses"],
        template=template
    )
    
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
    chain = prompt | llm
    
    return chain

def analyze_question(chain, question_text: str, responses: List[Dict], project_background: str) -> Dict:
    """Analyze responses for a single question."""
    # Format responses for the prompt
    formatted_responses = "\n".join([
        f"P{resp['participant_id']}: {resp['response']}"
        for resp in responses
    ])
    
    # Run the analysis
    result = chain.invoke({
        "project_background": project_background,
        "question_text": question_text,
        "num_participants": len(responses),
        "responses": formatted_responses
    })
    
    if hasattr(result, "content"):
        result = result.content
    
    # Parse the JSON response
    try:
        analysis = json.loads(result)
        return analysis
    except json.JSONDecodeError:
        print(f"Error parsing JSON for question: {question_text}")
        return None

def main():
    # Read the interview data
    questions_data = read_interview_data("usercue_interview_case_study_6Qs.xlsx")
    
    # Create the analysis pipeline
    chain = create_analysis_pipeline()
    
    # Analyze each question
    results = {}
    for question, responses in questions_data.items():
        print(f"Analyzing question: {question}")
        analysis = analyze_question(chain, question, responses, PROJECT_BACKGROUND)
        if analysis:
            results[question] = analysis
            
            # Save individual results
            with open(f"analysis_{question}.json", "w") as f:
                json.dump(analysis, f, indent=2)
    
    # Save all results
    with open("all_analyses.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
