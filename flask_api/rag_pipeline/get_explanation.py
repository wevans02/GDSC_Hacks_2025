'''
Generate response from GPT given the relevant chunks, context and user query
'''
from google.genai import types
from datetime import datetime

# were gonna use openai instead here
from openai import OpenAI
import os
from datetime import datetime
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# main generate function that puts together the prompt and runs
def generate(user_input: str, bylaws_data: str, city: str = None, context: str = None):
    now = datetime.now()
    # let LLm know the date so it knows what bylaw is most up-to-date
    date = now.strftime("%B %d, %Y")

    # verify fields
    if user_input is None:
        print("[WARN] LLM Generation: user_input is None")
    if bylaws_data is None:
        print("[WARN] LLM Generation: bylaws_data is None")
    if city is None:
        print("[WARN] LLM Generation: city is None")
    if context is None:
        print("[WARN] LLM Generation: context is None")

    # Ensure we always work with strings
    user_input = str(user_input or "").strip()
    bylaws_data = str(bylaws_data or "No bylaw sections available.")
    city = str(city or "Unknown City")
    context = str(context or "No prior conversation context.")

    # master prompt, this could always be tuned. 
    prompt = f"""You are Paralegal, a conversational chatbot as part of a RAG pipeline about {city}'s bylaws.

You are given the following bylaw sections:
{bylaws_data}

User Question:
{user_input}

Conversation History (chronological order, older first, newer later):
{context}

Instructions:
1. Keep your answers concise — 3-8 sentences maximum, unless the user explicitly asks for more detail. Use bullet points where suitable.
2. Answer the question using **specific and precise details** from the bylaw sections when relevant.
3. If the bylaws do not directly answer, provide the most relevant related information you can find in them.
4. If the user refers to previous questions or context, summarize them based on the Conversation History.
5. If you cannot answer at all from the given data, clearly provide what information you do have and explain that the question cannot be fully answered.
6. Some bylaw text may be **cut off at the start or end**. When responding, reconstruct cutoff words into full words so the answer reads naturally and is easy for the user to understand.
7. Always prefer clarity and accuracy over speculation.
8. If bylaw text contains fees with multiple effective dates, always select the fee that is in effect as of {date} and ignore older dates. Do not list past amounts unless the user explicitly asks for historical values.
9. If you are referring the user to an online page (ie. form to register to park overnight), it is preferrable to have that directly linked, only if you are sure it is accurate.
"""
    
    # debug print full constructed prompt
    # print("PROMPT: ", prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # or "gpt-4o" for higher accuracy
            messages=[
                {"role": "system", "content": "You are a precise legal chatbot named Paralegal."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=512,
            stream=False,  # set True for streaming mode, maybe later
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error contacting OpenAI: {e}"