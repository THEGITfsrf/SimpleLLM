from mem0 import Memory

config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen3:8b-q4_K_M",
            "temperature": 0,
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "mxbai-embed-large:latest",
            "embedding_dims": 1024,
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "embedding_model_dims": 1024,
            "collection_name": "mem0_v2",
            "path": "qdrant_local_db"
        }
    }
}

memory = Memory.from_config(config)

# CRUCIAL: Set infer=False so the local LLM doesn't break/skip the input
memory.add(
    "User prefers PyQt6 and dislikes port 5000",
    user_id="test-mem0",
    infer=False 
)

# Search with a semantic query
results = memory.search(
    query="What framework does the user like?", 
    filters={"user_id": "test-mem0"}
)

print(results)