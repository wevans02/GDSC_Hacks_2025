import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
'''
prompt:str, bylaws_list: list###
'''
def generate(user_input:str,bylaws_data:str):
    load_dotenv()
    port = int(os.environ.get("PORT", 5000))  # default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port)
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash" 


    # Initialize an empty string for the extra_info_text
    # extra_info_text = ""

    # # Loop through bylaws_data and concatenate all the information into extra_info_text
    # for i in bylaws_data:
    #     extra_info_text += "\n" + i["pdf_content"]  # Concatenate each item to the string

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""Based on the following bylaw sections: {bylaws_data}. 
                                    User Question: {user_input}. 
                                    Please carefully consider the bylaw sections and answer the user question using specific and precise information from the bylaw sections. 
                                    If you can not answer the users question directly, please provide related information to their question. 
                                    If you truly cannot answer at all using the bylaw data provided, briefly state to the user the information that you do have and that you cannot answer their question.
                                    Note that some of the data mauy be cut off at the start or at the end. when giving a response, please try to use full words, and 'fix' any cutoff words so that the response is easy to understand by the user.
                                     """), 
            ],
        ),
    ]

    print("Stuff here: ",bylaws_data, "\n\n\n")

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature = 0.5,
        top_p= 0.95,
        top_k=40,
        max_output_tokens= 8192,
        #system_instruction= f"which of these would best help answer the question {bylaws_data}.",
    )


    output = ""
    # Generate content using the model
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,

    ):
        print(chunk.text, end="")  # Print the generated chunk text
        output += chunk.text

    return output


