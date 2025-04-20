# Database Schema

## `public.embeddings` Table

This table stores the text content, metadata, and vector embeddings.

```sql
                 Table "public.embeddings"
  Column   |     Type     | Collation | Nullable | Default 
-----------+--------------+-----------+----------+---------
 id        | uuid         |           | not null | 
 metadata  | jsonb        |           |          | 
 contents  | text         |           |          | 
 embedding | vector(1536) |           |           | 
Indexes:
    "embeddings_pkey" PRIMARY KEY, btree (id)
    "embeddings_embedding_idx" diskann (embedding)
    "embeddings_meta_idx" gin (metadata jsonb_path_ops)
Triggers:
    ts_insert_blocker BEFORE INSERT ON embeddings FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker()
Number of child tables: 1 (Use \d+ to list them.)