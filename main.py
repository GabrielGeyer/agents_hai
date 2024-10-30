from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import duckdb
import json

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to restrict allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAI API key from environment variable
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Define request and response models
class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    response: str

#Tools
#sql tool
def execute_sql(sql_query):
  # handle exception
  try:
    result = duckdb.sql(sql_query)
    return result.to_df().to_string()
  except Exception as e:
    # e to string
    return str(e)
  
#Vega chart generation tool
def generate_vega_spec(question: str, data_url: str, mark_type: str = "bar", x_field: str = None, y_field: str = None, color_field: str = None) -> dict:
   spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": question,
        "data": {"url": data_url},
        "mark": mark_type,
        "encoding": {
            "x": {"field": x_field, "type": "quantitative" if mark_type != "text" else "ordinal"},
            "y": {"field": y_field, "type": "quantitative" if mark_type != "text" else "ordinal"},
        }
    }
   return spec

#tool Defenition for LLM
tools = [
  {
    "type": "function",
    "function": {
      "name": "execute_sql",
      "description": "Execute a SQL query on the dataset",
      "parameters": {
          "type": "object",
          "properties": {
              "sql_query": {
                  "type": "string",
                  "description": "The SQL query to execute.",
              },
              "additionalProperties": False,
          },
          "required": ["sql_query"],
      }
    }
},
{
    "type": "function",
    "function": {
      "name": "generate_vega_spec",
      "description": "Returns a Vega-Lite JSON specification that can be used to ",
      "parameters": {
          "type": "object",
          "properties": {
              "question": {
                    "type": "string",
                    "description": "The user's query or prompt, which provides context for the type of visualization."
                },
                "data_url": {
                    "type": "string",
                    "description": "URL of the data source to be visualized."
                },
                "mark_type": {
                    "type": "string",
                    "description": "The type of chart or mark to use in the visualization (e.g., 'bar', 'line', 'point').",
                    "default": "bar"
                },
                "x_field": {
                    "type": "string",
                    "description": "The field to be mapped to the x-axis.",
                    "default": None
                },
                "y_field": {
                    "type": "string",
                    "description": "The field to be mapped to the y-axis.",
                    "default": None
                }
              
          },
          "required": ["question", "data_url"],
          "additionalProperties": False,
      }
    }
}]

tool_map = {
    'execute_sql': execute_sql,
    'generate_vega_spec': generate_vega_spec,
}

# Endpoint to interact with OpenAI API via LangChain
@app.post("/query", response_model=QueryResponse)
async def query_openai(request: QueryRequest):
    try:
        prompt = f'''Question:{request.prompt} Data:'''
        system_prompt = 'You are a helpful assistant. Please only answer questions related to the dataset. You will have tools availible to help. '
        max_itterations = 6
       
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": prompt})

        i = 0
        while i < max_itterations:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools
            )

            if response.choices[0].message.tool_calls==None:
                break

            for tool_call in response.choices[0].message.tool_calls:
      

                # call the function
                arguments = json.loads(tool_call.function.arguments)
                function_to_call = tool_map[tool_call.function.name]
                result = function_to_call(**arguments) # save outcome

                # create a message containing the tool call result
                result_content = json.dumps({
                    **arguments,
                    "result": result
                })
                function_call_result_message = {
                    "role": "tool",
                    "content": result_content,
                    "tool_call_id": tool_call.id
                }
            

                # save the action request from LLM
                messages.append(response.choices[0].message)
                # save the action outcome for LLM
                messages.append(function_call_result_message)
            i += 1

        return QueryResponse(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')