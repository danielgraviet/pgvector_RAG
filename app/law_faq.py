import asyncio
from datetime import datetime
from database.vector_store import VectorStore
from services.synthesizer import Synthesizer
from timescale_vector import client
import colors

vec = VectorStore()

# --------------------------------------------------------------
# Coloring Output
# --------------------------------------------------------------
def print_response(query: str, response, section_title: str):
    print(f"\n{colors.SEPARATOR}--- {colors.HEADING}{section_title} ---")
    print(f"{colors.QUERY}Query: {query}")

    print(f"\n{colors.ANSWER}{response.answer}")

    print(f"\n{colors.HEADING}Thought process:")
    for thought in response.thought_process:
        print(f"{colors.THOUGHT}- {thought}")

    context_color = colors.CONTEXT_TRUE if response.enough_context else colors.CONTEXT_FALSE
    print(f"\n{colors.CONTEXT_LABEL}Context: {context_color}{response.enough_context}")
    print(f"{colors.SEPARATOR}-------------------------------------")
    
# --------------------------------------------------------------
# Input Any Question 
# --------------------------------------------------------------
async def main():
    section = "Relevant Question (Car Accident)"
    relevant_question = "What should I do after a car accident?"
    results = await vec.search(relevant_question, limit=3)
    response = Synthesizer.generate_response(question=relevant_question, context=results)
    print_response(relevant_question, response, section)
    
if __name__ == "__main__":
    asyncio.run(main())