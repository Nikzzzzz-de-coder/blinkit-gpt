from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import Optional, Dict
from groq import Groq
from supabase import create_client, Client
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

class AnyRequest(BaseModel):
    name: str

@app.post("/process-request/")
async def process_request(request: AnyRequest):
    try:
        system_prompt = """
You are a task based ordering assistant. Your job is to understand the task that the user wants to perform and return items required to complete that task effectively.

Instructions:
Format the task name – Remove any emojis and rephrase it for clarity.
Identify required items – List all necessary items with correct spellings and standard terminology.
Use hyphens (-) for list items, not asterisks
Return the response in the following exact format:
Task Name: [Clear and formatted task name]
Items:
- [Item 1]
- [Item 2]
- [...]
"""
        # Use environment variables for API keys
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.name}
            ],
            model="mixtral-8x7b-32768",
            temperature=0.1,
            max_tokens=1024
        )

        # After getting Groq response
        response_text = chat_completion.choices[0].message.content

        # After getting Groq response
        print("Groq Raw Response:")
        print(response_text)

        # Parse response with new format
        response_lines = [line.strip() for line in response_text.split('\n')]

        # Extract Task Name
        task_name = next((line.split("Task Name:")[1].strip() for line in response_lines
                        if line.startswith("Task Name:")), request.name)

        # Updated parsing logic
        items_start = next((i for i, line in enumerate(response_lines)
                          if line.lower().startswith("items")), -1)

        item_names = []
        if items_start != -1:
            for line in response_lines[items_start+1:]:
                # Handle both * and - bullets
                line = line.lstrip('*- ').strip()
                # Remove parenthetical comments
                line = line.split('(')[0].strip()
                if line:
                    item_names.append(line)
                else:
                    break  # Stop at empty line

        print("Parsed Items List:", item_names)

        # Use environment variables for Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        supabase: Client = create_client(supabase_url, supabase_key)

        items = []
        for name in item_names:
            matched = False

            # 1. Try exact match first
            response = supabase.table('video')\
                .select('quantity, units')\
                .ilike('name', f'%{name.lower()}%')\
                .execute()

            if response.data:
                items.append({
                    'name': name,
                    'quantity': response.data[0]['quantity'],
                    'units': response.data[0]['units']
                })
                continue

            # 2. If no exact match, try word by word OR first 3 letters based on word count
            words = name.lower().split()
            if len(words) > 1:
                # Multiple words: try word by word
                for word in words:
                    response = supabase.table('video')\
                        .select('quantity, units')\
                        .ilike('name', f'%{word}%')\
                        .execute()

                    if response.data:
                        items.append({
                            'name': name,
                            'quantity': response.data[0]['quantity'],
                            'units': response.data[0]['units']
                        })
                        matched = True
                        break
            else:
                # Single word: try first 3 letters
                if len(words[0]) >= 3:
                    response = supabase.table('video')\
                        .select('quantity, units')\
                        .ilike('name', f'%{words[0][:3]}%')\
                        .execute()

                    if response.data:
                        items.append({
                            'name': name,
                            'quantity': response.data[0]['quantity'],
                            'units': response.data[0]['units']
                        })
                        matched = True

            # If no matches found after all attempts
            if not matched and not response.data:
                items.append({'name': name, 'quantity': None, 'units': None})

        return {
            "status": "success",
            "task_name": task_name,
            "items": items
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)