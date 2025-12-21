"""Knowledge base search tools."""
from langchain.tools import tool
from typing import List, Dict, Any


@tool
def search_knowledge_base(query: str, vector_store, cache, k: int = 3) -> str:
    """Search the knowledge base for infrastructure answers.
    
    Args:
        query: The user's question
        vector_store: VectorStore instance
        cache: RedisCache instance
        k: Number of results to return
    
    Returns:
        Formatted search results or "No relevant information found"
    """
    # Check cache first
    cache_key = f"kb_search:{query}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Search vector store
    results = vector_store.search(query, k=k)
    
    if not results:
        return "No relevant information found in knowledge base."
    
    # Filter for high relevance only
    relevant_results = [r for r in results if r["relevance"] in ["high", "medium"]]
    
    if not relevant_results:
        return "No relevant information found in knowledge base."
    
    # Format results
    formatted = "Found the following relevant information:\n\n"
    for i, result in enumerate(relevant_results, 1):
        formatted += f"{i}. **Question**: {result['question']}\n"
        formatted += f"   **Answer**: {result['answer']}\n"
        formatted += f"   **Team**: {result['team']}\n"
        formatted += f"   **Tags**: {', '.join(result['tags'])}\n"
        formatted += f"   **Relevance**: {result['relevance']}\n\n"
    
    # Cache the result
    cache.set(cache_key, formatted, ttl=3600)
    
    return formatted


def create_knowledge_search_tool(vector_store, cache):
    """Factory function to create knowledge search tool with dependencies."""
    
    @tool
    def search_kb(query: str) -> str:
        """Search the infrastructure knowledge base for answers to common questions.
        Use this tool when a user asks about infrastructure, troubleshooting, or how-to questions."""
        return search_knowledge_base(query, vector_store, cache)
    
    return search_kb
