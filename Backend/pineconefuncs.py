import openai
import pinecone
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

# Initialize Pinecone
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_KEY"), environment="us-east1-aws")
index = pc.Index("notes")

client = openai.OpenAI(api_key=os.getenv("OPENAI_KEY"))


def index_markdown_note(markdown_text):
    # Vectorize text using OpenAI's Text-Embedding model
    response = client.embeddings.create(
        model="text-embedding-3-small", input=markdown_text
    )
    vector: pinecone.Vector = pinecone.Vector(
        id=str(uuid.uuid1()),
        values=response.data[0].embedding,
        metadata={"text": markdown_text},
    )

    index.upsert(vectors=[vector])


def find_relevant_notes(query_text):
    # Vectorize the query text
    response = client.embeddings.create(
        model="text-embedding-3-small", input=query_text
    )
    query_vector = response.data[0].embedding

    # Query Pinecone index
    results = index.query(vector=query_vector, top_k=10, include_metadata=True)

    relevant_notes = [
        result.metadata["text"] for result in results["matches"] if result.score >= 0.5
    ]

    if len(relevant_notes) <= 0:
        return ""

    prompt = (
        "Summarize the below notes into a single bulleted list, in markdown format only:\n\n"
        + "\n".join(relevant_notes)
    )

    summary = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        stop=None,
    )

    return summary.choices[0].message.content


# index.delete(delete_all=True)

# markdown_text = "intermediate representation to allow processing of pass data we in fact have two both Json ml a markdown tree and an HTML tree the extensible to add new dialects without having to rewrite the entire parsing mechanics having a good that's sweet the only test sweets we could find tested massive blocks of input and passing dependent on opening the HTML with exactly the same white space as the original implementation"
# index_markdown_note(markdown_text)
# query_text = "intermediate representation json ml markdown tree"
# print(find_relevant_notes(query_text))
