"""ChromaDB vector store wrapper."""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from langchain_ollama import OllamaEmbeddings
import json


class VectorStore:
    """Wrapper for ChromaDB vector store operations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "infrastructure_kb",
        embedding_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434"
    ):
        """Initialize ChromaDB client and embeddings."""
        self.host = host
        self.port = port
        self.collection_name = collection_name
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(
            model=embedding_model,
            base_url=ollama_base_url
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # Get or create collection directly
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            # Fallback: try without metadata
            self.collection = self.client.get_or_create_collection(
                name=collection_name
            )
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to vector store."""
        try:
            texts = []
            metadatas = []
            ids = []
            
            for doc in documents:
                combined_text = f"{doc['question']} {doc['answer']}"
                texts.append(combined_text)
                metadatas.append({
                    "question": doc["question"],
                    "answer": doc["answer"],
                    "team": doc.get("team", ""),
                    "tags": json.dumps(doc.get("tags", [])),
                    "entry_id": doc.get("id", "")
                })
                ids.append(doc.get("id", f"doc_{len(ids)}"))
            
            # Generate embeddings
            embeddings = self.embeddings.embed_documents(texts)
            
            # Add to ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            return True
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            return False
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search vector store for similar documents."""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]
                    
                    # Stricter thresholds for better matching
                    # ChromaDB uses L2 distance, lower is better
                    if distance < 0.3:
                        relevance = "high"
                    elif distance < 0.6:
                        relevance = "medium"
                    else:
                        relevance = "low"
                    
                    formatted_results.append({
                        "question": metadata.get("question", ""),
                        "answer": metadata.get("answer", ""),
                        "team": metadata.get("team", ""),
                        "tags": json.loads(metadata.get("tags", "[]")),
                        "entry_id": metadata.get("entry_id", ""),
                        "score": float(distance),
                        "relevance": relevance
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching vector store: {e}")
            return []
    
    def delete_collection(self) -> bool:
        """Delete the entire collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False
    
    def get_collection_count(self) -> int:
        """Get number of documents in collection."""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error getting collection count: {e}")
            return 0
