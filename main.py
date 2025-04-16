from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.database.vector_store import VectorStore
from app.services.synthesizer import Synthesizer
import pandas as pd
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI()
vector_store = VectorStore()  # Initialize VectorStore
synthesizer = Synthesizer()  # Initialize Synthesizer

class QueryRequest(BaseModel):
    question: str

@app.post("/faq/query")
async def query_faq(request: QueryRequest):
    try:
        logging.info(f"Received question: {request.question}")
        # Search the vector store using query_text
        results = vector_store.search(query_text=request.question, limit=3, return_dataframe=True)
        logging.info(f"Search results: {results.to_dict(orient='records')}")
        if not results.empty:
            # Generate synthesized response
            response = synthesizer.generate_response(question=request.question, context=results)
            logging.info(f"Returning answer: {response.answer}")
            return {
                "answer": response.answer,
                "thought_process": response.thought_process,
                "enough_context": response.enough_context
            }
        logging.info("No results found")
        return {
            "answer": "No relevant FAQ found.",
            "thought_process": ["No context available"],
            "enough_context": False
        }
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}", exc_info=True)
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
            .thought-process { margin-top: 10px; color: #555; }
            .context-true { color: green; }
            .context-false { color: red; }
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
                    if (!res.ok) {
                        const errorData = await res.json();
                        throw new Error(errorData.detail || "Server error");
                    }
                    const data = await res.json();
                    console.log("Response data:", data);
                    if (data && typeof data.answer === "string") {
                        let html = `<p><strong>Answer:</strong> ${data.answer}</p>`;
                        if (data.thought_process) {
                            html += `<div class="thought-process"><strong>Thought process:</strong><ul>`;
                            data.thought_process.forEach(thought => {
                                html += `<li>${thought}</li>`;
                            });
                            html += `</ul></div>`;
                        }
                        if (data.enough_context !== undefined) {
                            const contextClass = data.enough_context ? "context-true" : "context-false";
                            html += `<p><strong>Context:</strong> <span class="${contextClass}">${data.enough_context}</span></p>`;
                        }
                        responseDiv.innerHTML = html;
                    } else {
                        responseDiv.innerHTML = `<p><strong>Error:</strong> Invalid response format: ${JSON.stringify(data)}</p>`;
                    }
                } catch (error) {
                    console.error("Fetch error:", error);
                    responseDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
                }
            });
        </script>
    </body>
    </html>
    """