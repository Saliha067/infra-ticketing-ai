"""Knowledge Base Agent for RAG-based question answering."""
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from typing import Dict, Any


class KnowledgeAgent:
    """Agent specialized in searching and retrieving from knowledge base."""
    
    def __init__(
        self,
        llm: ChatOllama,
        vector_store,
        cache,
        system_prompt: str
    ):
        """Initialize Knowledge Agent."""
        self.llm = llm
        self.vector_store = vector_store
        self.cache = cache
        self.system_prompt = system_prompt
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """User question: {question}

Knowledge base search results:
{search_results}

Based on the search results, provide a clear and helpful answer. If the results are not relevant or no good match exists, clearly state that.""")
        ])
        
        # Create chain
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def search_knowledge_base(self, query: str, k: int = 3) -> Dict[str, Any]:
        """Search knowledge base and return results."""
        # Check cache
        cache_key = f"kb_search:{query}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Search vector store
        results = self.vector_store.search(query, k=k)
        
        # Cache results
        if results:
            self.cache.set(cache_key, results, ttl=3600)
        
        return results
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a question using the knowledge base."""
        # Search knowledge base
        search_results = self.search_knowledge_base(question)
        
        if not search_results:
            return {
                "found": False,
                "answer": None,
                "source": None,
                "confidence": "none"
            }
        
        # Filter for HIGH relevance only - be strict
        high_relevance = [r for r in search_results if r["relevance"] == "high" and r["score"] < 0.4]
        
        if not high_relevance:
            # No good match found
            return {
                "found": False,
                "answer": None,
                "source": None,
                "confidence": "low",
                "search_attempted": True
            }
        
        # Format search results for LLM
        formatted_results = "\n\n".join([
            f"Result {i+1}:\nQuestion: {r['question']}\nAnswer: {r['answer']}\nTeam: {r['team']}\nTags: {', '.join(r['tags'])}"
            for i, r in enumerate(high_relevance)
        ])
        
        # Get LLM to synthesize answer
        try:
            answer = self.chain.invoke({
                "question": question,
                "search_results": formatted_results
            })
            
            # Get best match
            best_match = high_relevance[0]
            
            return {
                "found": True,
                "answer": answer,
                "source": best_match,
                "confidence": best_match["relevance"],
                "all_results": high_relevance
            }
        except Exception as e:
            print(f"Error generating answer: {e}")
            return {
                "found": False,
                "answer": None,
                "source": None,
                "confidence": "error",
                "error": str(e)
            }
