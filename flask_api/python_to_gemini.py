from google import genai
from google.genai import types
from clients import gemini_client
from datetime import datetime

def generate(user_input: str, bylaws_data: str, city: str = None, context: str = None):
    now = datetime.now()
    easy_str = now.strftime("%B %d, %Y")   # e.g. "September 29, 2025"

    if user_input is None:
        print("⚠️ Warning: user_input is None")
    if bylaws_data is None:
        print("⚠️ Warning: bylaws_data is None")
    if city is None:
        print("⚠️ Warning: city is None")
    if context is None:
        print("⚠️ Warning: context is None")

        
    # Ensure we always work with strings
    user_input = str(user_input or "").strip()
    bylaws_data = str(bylaws_data or "No bylaw sections available.")
    city = str(city or "Unknown City")
    context = str(context or "No prior conversation context.")

    prompt = f"""You are Paralegal, a conversational chatbot as part of a RAG pipeline about {city}'s bylaws.

You are given the following bylaw sections:
{bylaws_data}

User Question:
{user_input}

Conversation History (chronological order, older first, newer later):
{context}

Instructions:
1. Keep your answers concise — 3–6 sentences maximum, unless the user explicitly asks for more detail. Use bullet points where suitable.
2. Answer the question using **specific and precise details** from the bylaw sections when relevant.
3. If the bylaws do not directly answer, provide the most relevant related information you can find in them.
4. If the user refers to previous questions or context, summarize them based on the Conversation History.
5. If you cannot answer at all from the given data, clearly state what information you do have and explain that the question cannot be fully answered.
6. Some bylaw text may be **cut off at the start or end**. When responding, reconstruct cutoff words into full words so the answer reads naturally and is easy for the user to understand.
7. Always prefer clarity and accuracy over speculation.
8. If bylaw text contains fees with multiple effective dates, always select the fee that is in effect as of {easy_str} and ignore older dates. Do not list past amounts unless the user explicitly asks for historical values.
"""
    print("PROMPT: ", prompt)
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature=0.5,
        top_p=0.95,
        top_k=40,
        max_output_tokens=512,
    )

    output = ""
    try:
        for chunk in gemini_client.models.generate_content_stream(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=generate_content_config,
        ):
            if hasattr(chunk, "text") and chunk.text:
                output += chunk.text
    except Exception as e:
        # Fail gracefully so your API never crashes
        return f"Error contacting Gemini: {e}"

    return output if output else "No response generated."
