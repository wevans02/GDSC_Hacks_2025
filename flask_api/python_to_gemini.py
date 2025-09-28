from google import genai
from google.genai import types
from clients import gemini_client

def generate(user_input: str, bylaws_data: str, city: str = None, context: str = None):

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

Context:
{context}

Instructions:
1. Answer the question using **specific and precise details** from the bylaw sections.
2. If the bylaws do not directly answer, provide the most relevant related information you can find in them.
3. If you cannot answer at all from the given data, clearly state what information you do have and explain that the question cannot be fully answered.
4. Some bylaw text may be **cut off at the start or end**. When responding, reconstruct cutoff words into full words so the answer reads naturally and is easy for the user to understand.
5. Always prefer clarity and accuracy over speculation.
6. Be concise in your answers.
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
        max_output_tokens=8192,
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
