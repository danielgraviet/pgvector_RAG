import asyncpg
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import json
from pgvector.asyncpg import Vector

load_dotenv()

class VectorStore:
    def __init__(self, database_url: str, embedding_model: str = "text-embedding-3-small"):
        self._database_url = database_url
        self._pool = None
        self._openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) 
        self._embeddings_model = embedding_model
        
    async def connect(self):
        if self._pool is None: #shared set of read-to-use connections to db. faster. 
            self._pool = await asyncpg.create_pool(dsn=self._database_url)
            
    async def close(self):
        if self._pool:
            self._pool.close()
            
    async def generate_embedding(self, text: str) -> list[float]:
        response = await self._openai.embeddings.create(
            model=self._embeddings_model,
            input = text
        )
        return response.data[0].embedding
    
    async def create_tables(self):
        """Create the embeddings table if it doesn’t exist."""
        await self.connect()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS public.embeddings (
                    id uuid PRIMARY KEY,
                    metadata jsonb,
                    contents text,
                    embedding vector(1536)
                );
            """)
            
    async def create_index(self):
        """Create a vector index if it doesn’t exist."""
        await self.connect()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
                ON public.embeddings USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
    async def upsert(self, records):
        await self.connect()
        if hasattr(records, "to_dict"):  # If it's a DataFrame
            records = records.to_dict(orient="records")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for rec in records:
                    vector_value = "[" + ",".join(map(str, rec["embedding"])) + "]"
                    
                    await conn.execute("""
                    INSERT INTO public.embeddings (id, metadata, contents, embedding)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE
                    SET metadata = EXCLUDED.metadata,
                        contents = EXCLUDED.contents,
                        embedding = EXCLUDED.embedding;
                """,
                rec["id"],
                json.dumps(rec["metadata"]),
                rec["contents"],
                vector_value
                )
    
    async def insert_faq_embedding(self, faq_question_and_answer: str):
        embedding = self.generate_embedding(faq_question_and_answer)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO documents (faq_question_and_answer, embedding) VALUES ($1, $2)",
                faq_question_and_answer,
                embedding
            )
            
    async def similarity_search(self, query: str, k: int = 5):
        """Search for documents most similar to query text."""
        query_embedding = await self.generate_embedding(query)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content
                FROM documents
                ORDER BY embedding <-> $1
                LIMIT $2
                """,
                query_embedding,
                k
            )
        return [dict(row) for row in rows]
        
        