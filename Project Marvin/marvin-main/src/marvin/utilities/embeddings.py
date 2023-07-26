from typing import List

import openai

import marvin


async def create_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """Create OpenAI embeddings for a list of texts."""
    embeddings = await openai.Embedding.acreate(
        input=[text.replace("\n", " ") for text in texts],
        engine=marvin.settings.embedding_engine,
    )

    return [
        r["embedding"] for r in sorted(embeddings["data"], key=lambda x: x["index"])
    ]
