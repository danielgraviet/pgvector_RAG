from datetime import datetime
from database.vector_store import VectorStore
from services.synthesizer import Synthesizer
from timescale_vector import client
import colors

# Initialize VectorStore
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
# Shipping question
# --------------------------------------------------------------

section = "Relevant Question (Shipping)"
relevant_question = "What are your shipping options?"
results = vec.search(relevant_question, limit=3)
response = Synthesizer.generate_response(question=relevant_question, context=results)
print_response(relevant_question, response, section)

# --------------------------------------------------------------
# Irrelevant question
# --------------------------------------------------------------

section = "Irrelevant Question (Weather)"
irrelevant_question = "What is the weather in Tokyo?"
results = vec.search(irrelevant_question, limit=3)
response = Synthesizer.generate_response(question=irrelevant_question, context=results)
print_response(irrelevant_question, response, section)

# --------------------------------------------------------------
# Metadata filtering
# --------------------------------------------------------------
section = "Metadata Filter (Shipping Category)"
metadata_filter = {"category": "Shipping"}
results = vec.search(relevant_question, limit=3, metadata_filter=metadata_filter)
response = Synthesizer.generate_response(question=relevant_question, context=results)
# Only printing the answer for brevity in this example,
# but you could use print_response if you want full output
print(f"\n{colors.SEPARATOR}--- {colors.HEADING}{section} ---")
print(f"{colors.QUERY}Query: {relevant_question}")
print(f"{colors.QUERY}Filter: {metadata_filter}")
print(f"\n{colors.ANSWER}{response.answer}") # Assuming the answer is the same
print(f"{colors.SEPARATOR}-------------------------------------")

# --------------------------------------------------------------
# Advanced filtering using Predicates
# --------------------------------------------------------------
print(f"\n{colors.SEPARATOR}--- {colors.HEADING}Predicate Examples ---")
print(f"{colors.QUERY}Query: {relevant_question}")

predicates_eq = client.Predicates("category", "==", "Shipping")
results_eq = vec.search(relevant_question, limit=3, predicates=predicates_eq)
print(f"{colors.THOUGHT}- Predicate: category == 'Shipping' -> Found {len(results_eq)} results (example)")

predicates_or = client.Predicates("category", "==", "Shipping") | client.Predicates(
    "category", "==", "Services"
)
results_or = vec.search(relevant_question, limit=3, predicates=predicates_or)
print(f"{colors.THOUGHT}- Predicate: category == 'Shipping' OR category == 'Services' -> Found {len(results_or)} results (example)")


predicates_and = client.Predicates("category", "==", "Shipping") & client.Predicates(
    "created_at", ">", "2024-09-01" # Assuming created_at is a searchable field
)

print(f"{colors.THOUGHT}- (Skipping AND predicate example as 'created_at' might not be in metadata)")

# --------------------------------------------------------------
# Time-based filtering
# --------------------------------------------------------------
print(f"\n{colors.SEPARATOR}--- {colors.HEADING}Time-based Filter Examples ---")
print(f"{colors.QUERY}Query: {relevant_question}")

# September — Returning results
time_range_sep = (datetime(2024, 9, 1), datetime(2024, 9, 30))
results_sep = vec.search(relevant_question, limit=3, time_range=time_range_sep)
print(f"{colors.THOUGHT}- Time Range: Sep 2024 -> Found {len(results_sep)} results (example)")


# August — Not returning any results
time_range_aug = (datetime(2024, 8, 1), datetime(2024, 8, 30))
results_aug = vec.search(relevant_question, limit=3, time_range=time_range_aug)
print(f"{colors.THOUGHT}- Time Range: Aug 2024 -> Found {len(results_aug)} results (example)")
print(f"{colors.SEPARATOR}-------------------------------------")