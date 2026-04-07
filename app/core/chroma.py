import logging
import os
from typing import List

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class CustomOpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []

        try:
            response = self.client.embeddings.create(input=input, model=self.model_name)
            data = sorted(response.data, key=lambda x: x.index)
            return [d.embedding for d in data]
        except Exception as e:
            logger.warning(f"Embedding API Error with model '{self.model_name}': {e}")
            # Fallback: try with a different model if the primary fails
            try:
                logger.info("Retrying with fallback model 'text-embedding-3-small'...")
                response = self.client.embeddings.create(
                    input=input, model="text-embedding-3-small"
                )
                data = sorted(response.data, key=lambda x: x.index)
                return [d.embedding for d in data]
            except Exception as fallback_e:
                logger.error(f"Fallback embedding also failed: {fallback_e}")
                raise RuntimeError(f"Embedding API Error: {fallback_e}")


def get_chroma_client():
    from chromadb.config import Settings
    try:
        # Use HttpClient to connect to Chroma via settings
        return chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False)
        )
    except Exception as e:
        logger.error(f"Failed to initialize Chroma HttpClient: {e}")
        return None

def get_property_collection():
    client = get_chroma_client()
    if not client:
        logger.error("Chroma client is not available. Returning None for collection.")
        return None

    # Determine the best embedding model based on the LLM provider
    embedding_model = "text-embedding-ada-002"
    if "openrouter" in settings.LLM_BASE_URL.lower():
        embedding_model = "openai/text-embedding-3-small"

    # Use the configured OpenRouter API key
    api_key = settings.OPENROUTER_API_KEY

    ef = CustomOpenAIEmbeddingFunction(
        api_key=api_key, base_url=settings.LLM_BASE_URL, model_name=embedding_model
    )

    try:
        return client.get_or_create_collection(
            name="property_documents", embedding_function=ef
        )
    except Exception as e:
        logger.error(f"Failed to get or create Chroma collection: {e}")
        return None
