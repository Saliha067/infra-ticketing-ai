"""Simple test script to verify the setup."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import os

load_dotenv()

def test_ollama():
    """Test Ollama connection."""
    print("\n1. Testing Ollama...")
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        response = llm.invoke("Say 'test successful' in 2 words")
        print(f"   ✓ Ollama working: {response.content}")
        return True
    except Exception as e:
        print(f"   ✗ Ollama failed: {e}")
        return False


def test_redis():
    """Test Redis connection."""
    print("\n2. Testing Redis...")
    try:
        from src.utils.cache import RedisCache
        cache = RedisCache(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379))
        )
        if cache.ping():
            cache.set("test_key", "test_value", ttl=10)
            value = cache.get("test_key")
            print(f"   ✓ Redis working: {value}")
            return True
        else:
            print("   ✗ Redis not responding")
            return False
    except Exception as e:
        print(f"   ✗ Redis failed: {e}")
        return False


def test_postgres():
    """Test PostgreSQL connection."""
    print("\n3. Testing PostgreSQL...")
    try:
        from src.db.models import init_db
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        engine = init_db(db_url)
        print("   ✓ PostgreSQL working")
        return True
    except Exception as e:
        print(f"   ✗ PostgreSQL failed: {e}")
        return False


def test_chromadb():
    """Test ChromaDB connection."""
    print("\n4. Testing ChromaDB...")
    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", 8000)),
            settings=Settings(anonymized_telemetry=False)
        )
        client.heartbeat()
        print("   ✓ ChromaDB working")
        return True
    except Exception as e:
        print(f"   ✗ ChromaDB failed: {e}")
        return False


def test_vector_store():
    """Test vector store functionality."""
    print("\n5. Testing Vector Store...")
    try:
        from src.db.vector_store import VectorStore
        
        vs = VectorStore(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", 8000)),
            collection_name="test_collection",
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        # Add test document
        test_doc = [{
            "id": "test_1",
            "question": "How to restart a pod?",
            "answer": "Use kubectl restart",
            "team": "platform",
            "tags": ["kubernetes"]
        }]
        
        vs.add_documents(test_doc)
        
        # Search
        results = vs.search("restart pod", k=1)
        if results:
            print(f"   ✓ Vector store working: Found {len(results)} results")
            # Cleanup
            vs.delete_collection()
            return True
        else:
            print("   ✗ Vector store search failed")
            return False
    except Exception as e:
        print(f"   ✗ Vector store failed: {e}")
        return False


def test_agents():
    """Test agent functionality."""
    print("\n6. Testing Agents...")
    try:
        from src.agents.knowledge_agent import KnowledgeAgent
        from src.agents.router_agent import RouterAgent
        from src.utils.cache import RedisCache
        from src.db.vector_store import VectorStore
        from langchain_ollama import ChatOllama
        from config.prompts import KNOWLEDGE_BASE_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT
        
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.1
        )
        
        cache = RedisCache()
        vs = VectorStore(collection_name="test_agents")
        
        # Test knowledge agent
        ka = KnowledgeAgent(llm, vs, cache, KNOWLEDGE_BASE_SYSTEM_PROMPT)
        
        # Test router agent
        ra = RouterAgent(llm, ROUTER_SYSTEM_PROMPT)
        routing = ra.route_inquiry("Database connection issue", "database")
        
        print(f"   ✓ Agents working: Routed to '{routing['team']}' team")
        
        # Cleanup
        vs.delete_collection()
        return True
    except Exception as e:
        print(f"   ✗ Agents failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Infrastructure Inquiry Bot - System Tests")
    print("=" * 60)
    
    tests = [
        test_ollama,
        test_redis,
        test_postgres,
        test_chromadb,
        test_vector_store,
        test_agents
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All systems operational! Ready to start the bot.")
        print("\nRun the bot with:")
        print("  python src/main.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nMake sure:")
        print("  1. docker-compose up -d")
        print("  2. ollama serve (in another terminal)")
        print("  3. All environment variables are set in .env")


if __name__ == "__main__":
    main()
