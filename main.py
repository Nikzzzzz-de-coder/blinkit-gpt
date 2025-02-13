from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles  # Import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Optional, List
from groq import Groq
from supabase import create_client, Client
import uvicorn
from fastapi.responses import FileResponse

# Secure API Keys from Environment Variables
GROQ_API_KEY= ""
SUPABASE_URL= ""
SUPABASE_KEY= "" 

# Ensure API keys exist
if not GROQ_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing API keys. Ensure they are set in the .env file.")

# Initialize FastAPI
app = FastAPI()

# ===== Adding CORS Middleware =====
# This middleware will handle preflight OPTIONS requests and add the necessary headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allows all origins - adjust this in production for security
    allow_credentials=True,
    allow_methods=["*"],       # Allow all HTTP methods
    allow_headers=["*"],       # Allow all headers
)

# Get the path to the backend directory
backend_path = os.getcwd()

# Get the parent directory (project root) and join with 'frontend'
frontend_path = os.path.join(os.path.dirname(backend_path), "frontend")

try:
    if os.path.exists(frontend_path):
        print(f"📁 Mounting frontend directory from: {frontend_path}")
        # Mount static files at /static instead of root /
        app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="frontend")
        
        # Add a root route to serve index.html
        @app.get("/")
        async def serve_index():
            return FileResponse(os.path.join(frontend_path, "index.html"))
    else:
        print(f"⚠️ WARNING: Frontend directory not found at: {frontend_path}")
except Exception as e:
    print(f"❌ Error mounting frontend: {str(e)}")

    
# Pydantic Model for Request Validation
class AnyRequest(BaseModel):
    name: str

@app.post("/process-request/")
async def process_request(request: AnyRequest) -> dict:
    try:
        # Define the System Prompt
        system_prompt = """
You are a task-based ordering assistant. Your job is to understand the task that the user wants to perform and return items required to complete that task effectively.

Instructions:
- Format the task name – Remove any emojis and rephrase it for clarity.
- Identify required items – List all necessary items with correct spellings and standard terminology.
- Use hyphens (-) for list items, not asterisks.
- Return the response in the following exact format:
Task Name: [Clear and formatted task name]
Items:
- [Item 1]
- [Item 2]
- [...]
"""

        # Initialize Groq Client
        client = Groq(api_key=GROQ_API_KEY)

        # Get user input - directly access the name field from the Pydantic model
        user_input = request.name

        # Call Groq API for response
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            model="mixtral-8x7b-32768",
            temperature=0.1,
            max_tokens=1024
        )

        # Extract the response
        response_text = chat_completion.choices[0].message.content
        print("Groq Raw Response:", response_text)

        # Parse response with new format
        response_lines: List[str] = response_text.split('\n')

        # Extract Task Name (With Fallback)
        task_name: str = next(
            (line.split("Task Name:")[1].strip() for line in response_lines if line.startswith("Task Name:")),
            "Untitled Task"
        )

        # Extract Items List
        items_start: int = next(
            (i for i, line in enumerate(response_lines) if line.lower().strip().startswith("items")),
            -1
        )

        item_names: List[str] = []
        if items_start != -1:
            for line in response_lines[items_start + 1:]:
                line = line.lstrip('*- ').strip()  # Remove bullets
                line = line.split('(')[0].strip()  # Remove parenthetical comments
                if line:
                    item_names.append(line)
                else:
                    break  # Stop at empty line

        print("Parsed Items List:", item_names)

        # Initialize Supabase Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Fetch item details from the database
        items = []
        for name in item_names:
            response = supabase.table('video').select('quantity, units').ilike('name', f'%{name.lower()}%').execute()

            if response.data:
                items.append({
                    'name': name,
                    'quantity': response.data[0].get('quantity', "Unknown"),
                    'units': response.data[0].get('units', "Unknown")
                })
            else:
                items.append({'name': name, 'quantity': None, 'units': None})  # No match found

        return {
            "status": "success",
            "task_name": task_name,
            "items": items
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# Run the FastAPI Server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
