import embed_vectors
#for git
from dotenv import load_dotenv
import os
#pymango
import pymongo


def query_database(query_text:str, database_name:str, collection_name:str):

  load_dotenv()

  DATABASE_LOGIN = os.getenv("DATABASE_LOGIN") #DATABASE_LOGIN is in the form username:password

  uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

  # connect to your Atlas cluster
  client = pymongo.MongoClient(uri)

  #TODO
  #generate this vector using the query_text
  query_vector = embed_vectors.embed_text(query_text)


  # define pipeline
  pipeline = [
    {
      '$vectorSearch': {
        'index': 'vector_index', 
        'path': 'plot_embedding', 
        'queryVector': query_vector,
        'numCandidates': 200, 
        'limit': 10
      }
    }, {
      '$project': {
        '_id': 0,  
        'title': 1, 
        'pdf': 1,
        'pdf_content':1,
        'score': {
          '$meta': 'vectorSearchScore'
        }
      }
    }
  ]

  # run pipeline
  result = client[database_name][collection_name].aggregate(pipeline)

  
  return result 

# result = query_database("can i park on bartly drive?", "bylaws", "all_bylaws")


# import python_to_gemini

# python_to_gemini.generate("can i park on bartly drive?",result)
