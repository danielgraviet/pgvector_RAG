from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.database.vector_store import VectorStore
import os
import logging

app = FastAPI()
vector_store = VectorStore()  # Initialize your VectorStore

class QueryRequest(BaseModel):
    question: str

@app.post("/faq/query")
async def query_faq(request: QueryRequest):
    try:
        # Generate embedding for the question
        query_embedding = vector_store.get_embedding(request.question)
        # Search the vector store (adjust based on your VectorStore search method)
        results = vector_store.vec_client.search(
            embedding=query_embedding,
            limit=1  # Get the most relevant FAQ
        )
        if results:
            # Assuming results return (id, metadata, content, embedding, score)
            return {"answer": results[0][2]}  # Return content field
        return {"answer": "No relevant FAQ found."}
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def get_faq_form():
    # Simple HTML form for the web interface
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FAQ System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 50px; }
            #faq-form { max-width: 600px; }
            input { width: 100%; padding: 10px; margin: 10px 0; }
            button { padding: 10px 20px; }
            #response { margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>FAQ System</h1>
        <form id="faq-form">
            <input type="text" id="question" placeholder="Ask a question..." required>
            <button type="submit">Submit</button>
        </form>
        <div id="response"></div>
        <script>
            document.getElementById("faq-form").addEventListener("submit", async (e) => {
                e.preventDefault();
                const question = document.getElementById("question").value;
                const responseDiv = document.getElementById("response");
                try {
                    const res = await fetch("/faq/query", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ question })
                    });
                    const data = await res.json();
                    responseDiv.innerHTML = `<p><strong>Answer:</strong> ${data.answer}</p>`;
                } catch (error) {
                    responseDiv.innerHTML = `<p>Error: ${error.message}</p>`;
                }
            });
        </script>
    </body>
    </html>
    """