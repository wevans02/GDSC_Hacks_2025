from google import genai
from google.genai import types
from clients import gemini_client

def generate(user_input:str, bylaws_data:str):
    # Check if the API key was set during initialization
    # if not genai.conf.api_key:
    #     print("Error: Gemini API key is not configured.")
    #     return "Sorry, the AI service is currently unavailable."

    # --- Initialize the model here ---
    # model = genai.GenerativeModel("gemini-2.5-flash-lite") # Updated model name

    # Initialize an empty string for the extra_info_text
    # extra_info_text = ""

    # # Loop through bylaws_data and concatenate all the information into extra_info_text
    # for i in bylaws_data:
    #     extra_info_text += "\n" + i["pdf_content"]  # Concatenate each item to the string

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""
                    You are Paralegal, a conversational chatbot as part of a RAG pipeline about torontos bylaws.
                                     
                    You are given the following bylaw sections:
                    {bylaws_data}

                    User Question:
                    {user_input}

                    Instructions:
                    1. Answer the question using **specific and precise details** from the bylaw sections.
                    2. If the bylaws do not directly answer, provide the most relevant related information you can find in them.
                    3. If you cannot answer at all from the given data, clearly state what information you do have and explain that the question cannot be fully answered.
                    4. Some bylaw text may be **cut off at the start or end**. When responding, reconstruct cutoff words into full words so the answer reads naturally and is easy for the user to understand.
                    5. Always prefer clarity and accuracy over speculation.
                    6. Be concise in your answers.
                    """), 
            ],
        ),
    ]

    print("Stuff here: ",bylaws_data, "\n\n\n")

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature=0.5,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
    )

    output = ""
    for chunk in gemini_client.models.generate_content_stream(
        model="gemini-2.5-flash-lite",
        contents=contents,
        config=generate_content_config,
    ):
        output += chunk.text
    return output


