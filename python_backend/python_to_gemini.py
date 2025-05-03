import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
'''
prompt:str, bylaws_list: list###
'''
def generate(user_input:str,bylaws_data):
    load_dotenv()
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash-lite"


    # Initialize an empty string for the extra_info_text
    extra_info_text = ""

    # Loop through bylaws_data and concatenate all the information into extra_info_text
    for i in bylaws_data:
        extra_info_text += "\n" + i["pdf"]  # Concatenate each item to the string

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_input + f"which of these would best help answer the question {extra_info_text}."), 
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature = 0,
        top_p= 0.95,
        top_k=40,
        max_output_tokens= 8192,
        system_instruction= f"which of these would best help answer the question {extra_info_text}.",
    )



    # Generate content using the model
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,

    ):
        print(chunk.text, end="")  # Print the generated chunk text


