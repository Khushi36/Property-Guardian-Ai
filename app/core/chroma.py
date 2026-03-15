from typing import List
import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from app.core.config import settings
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class CustomOpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
            
        try:
            response = self.client.embeddings.create(
                input=input,
                model=self.model_name
            )
            data = sorted(response.data, key=lambda x: x.index)
            return [d.embedding for d in data]
        except Exception as e:
            logger.warning(f"Embedding API Error with model '{self.model_name}': {e}")
            # Fallback: try with a different model if the primary fails
            try:
                logger.info("Retrying with fallback model 'text-embedding-3-small'...")
                response = self.client.embeddings.create(
                    input=input,
                    model="text-embedding-3-small"
                )
                data = sorted(response.data, key=lambda x: x.index)
                return [d.embedding for d in data]
            except Exception as fallback_e:
                logger.error(f"Fallback embedding also failed: {fallback_e}")
                raise RuntimeError(f"Embedding API Error: {fallback_e}")

def get_chroma_client():
    if not os.path.exists(settings.CHROMA_PERSIST_DIRECTORY):
        os.makedirs(settings.CHROMA_PERSIST_DIRECTORY)
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)

def get_property_collection():
    client = get_chroma_client()
    
    # Determine the best embedding model based on the LLM provider
    embedding_model = "text-embedding-ada-002"
    if "openrouter" in settings.LLM_BASE_URL.lower():
        embedding_model = "openai/text-embedding-3-small"
    
    # Use the configured OpenRouter API key
    api_key = settings.OPENROUTER_API_KEY

    ef = CustomOpenAIEmbeddingFunction(
        api_key=api_key,
        base_url=settings.LLM_BASE_URL,
        model_name=embedding_model
    )

    return client.get_or_create_collection(
        name="property_documents",
        embedding_function=ef
    )
