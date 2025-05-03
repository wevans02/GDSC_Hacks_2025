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
  query_vector = []

  # define pipeline
  pipeline = [
    {
      '$vectorSearch': {
        'index': 'vector_index', 
        'path': 'plot_embedding', 
        'queryVector': query_vector,
        'numCandidates': 150, 
        'limit': 10
      }
    }, {
      '$project': {
        '_id': 0, 
        'title': 1, 
        'pdf': 1, 
        'score': {
          '$meta': 'vectorSearchScore'
        }
      }
    }
  ]

  #TODO optional: loop this for multiple collections if that is how to data ends up
  # run pipeline
  result = client[database_name][collection_name].aggregate(pipeline)

  # print results
  for i in result:
      print(i)
  
  return result 
  