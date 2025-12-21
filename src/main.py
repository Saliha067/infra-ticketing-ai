"""Main application entry point."""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger
from src.utils.cache import RedisCache
from src.db.models import init_db, get_session_maker
from src.db.vector_store import VectorStore
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.router_agent import RouterAgent
from src.agents.supervisor import SupervisorAgent
from src.tools.jira_tools import create_jira_tools
from src.slack_bot import SlackBot
from langchain_ollama import ChatOllama

from config.prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    KNOWLEDGE_BASE_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT
)


def load_knowledge_base(vector_store: VectorStore, logger):
    """Load knowledge base from JSON file."""
    kb_file = Path("config/knowledge_base.json")
    
    if not kb_file.exists():
        logger.warning(f"Knowledge base file not found: {kb_file}")
        return False
    
    try:
        with open(kb_file, 'r') as f:
            documents = json.load(f)
        
        logger.info(f"Loading {len(documents)} documents into vector store...")
        success = vector_store.add_documents(documents)
        
        if success:
            count = vector_store.get_collection_count()
            logger.info(f"Knowledge base loaded successfully. Total documents: {count}")
            return True
        else:
            logger.error("Failed to load knowledge base")
            return False
    
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        return False


def check_dependencies(logger):
    """Check if all required services are available."""
    issues = []
    
    # Check Ollama
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        llm.invoke("test")
        logger.info("✓ Ollama is available")
    except Exception as e:
        issues.append(f"✗ Ollama not available: {e}")
    
    # Check Redis
    try:
        cache = RedisCache(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379))
        )
        if cache.ping():
            logger.info("✓ Redis is available")
        else:
            issues.append("✗ Redis not responding")
    except Exception as e:
        issues.append(f"✗ Redis not available: {e}")
    
    # Check PostgreSQL
    try:
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        engine = init_db(db_url)
        logger.info("✓ PostgreSQL is available")
    except Exception as e:
        issues.append(f"✗ PostgreSQL not available: {e}")
    
    # Check ChromaDB
    try:
        import chromadb
        client = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", 8000))
        )
        client.heartbeat()
        logger.info("✓ ChromaDB is available")
    except Exception as e:
        issues.append(f"✗ ChromaDB not available: {e}")
    
    return issues


def main():
    """Main application entry point."""
    # Load environment variables
    load_dotenv()
    
    # Setup logger
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger = setup_logger("infra_bot", log_level)
    
    logger.info("=" * 60)
    logger.info("Infrastructure Inquiry Bot Starting...")
    logger.info("=" * 60)
    
    # Check dependencies
    logger.info("\nChecking dependencies...")
    issues = check_dependencies(logger)
    
    if issues:
        logger.error("\n⚠️  Dependency issues found:")
        for issue in issues:
            logger.error(f"  {issue}")
        logger.error("\nPlease ensure all services are running:")
        logger.error("  docker-compose up -d")
        logger.error("  ollama serve")
        sys.exit(1)
    
    logger.info("\n✅ All dependencies are available\n")
    
    # Initialize components
    logger.info("Initializing components...")
    
    # 1. Initialize LLM
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.1
    )
    logger.info(f"✓ LLM initialized: {os.getenv('OLLAMA_MODEL', 'llama3.1:8b')}")
    
    # 2. Initialize cache
    cache = RedisCache(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD") or None
    )
    logger.info("✓ Cache initialized")
    
    # 3. Initialize database
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    engine = init_db(db_url)
    SessionMaker = get_session_maker(engine)
    db_session = SessionMaker()
    logger.info("✓ Database initialized")
    
    # 4. Initialize vector store
    vector_store = VectorStore(
        host=os.getenv("CHROMA_HOST", "localhost"),
        port=int(os.getenv("CHROMA_PORT", 8000)),
        embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    logger.info("✓ Vector store initialized")
    
    # Load knowledge base
    load_knowledge_base(vector_store, logger)
    
    # 5. Initialize agents
    knowledge_agent = KnowledgeAgent(
        llm=llm,
        vector_store=vector_store,
        cache=cache,
        system_prompt=KNOWLEDGE_BASE_SYSTEM_PROMPT
    )
    logger.info("✓ Knowledge agent initialized")
    
    router_agent = RouterAgent(
        llm=llm,
        system_prompt=ROUTER_SYSTEM_PROMPT
    )
    logger.info("✓ Router agent initialized")
    
    supervisor_agent = SupervisorAgent(
        llm=llm,
        knowledge_agent=knowledge_agent,
        router_agent=router_agent,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT
    )
    logger.info("✓ Supervisor agent initialized")
    
    # 6. Initialize JIRA tools (optional)
    jira_tools = create_jira_tools(
        jira_url=os.getenv("JIRA_URL"),
        jira_email=os.getenv("JIRA_EMAIL"),
        jira_token=os.getenv("JIRA_API_TOKEN"),
        project_key=os.getenv("JIRA_PROJECT_KEY")
    )
    if os.getenv("JIRA_URL"):
        logger.info("✓ JIRA tools initialized")
    else:
        logger.info("⚠ JIRA integration disabled (not configured)")
    
    # 7. Initialize Slack bot
    slack_bot = SlackBot(
        bot_token=os.getenv("SLACK_BOT_TOKEN"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        supervisor_agent=supervisor_agent,
        jira_tools=jira_tools,
        db_session=db_session,
        logger=logger
    )
    logger.info("✓ Slack bot initialized")
    
    logger.info("\n" + "=" * 60)
    logger.info("🚀 Infrastructure Inquiry Bot is ready!")
    logger.info("=" * 60)
    logger.info(f"  Model: {os.getenv('OLLAMA_MODEL', 'llama3.1:8b')}")
    logger.info(f"  Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"  JIRA: {'Enabled' if os.getenv('JIRA_URL') else 'Disabled'}")
    logger.info("=" * 60 + "\n")
    
    # Start the bot
    try:
        slack_bot.start()
    except KeyboardInterrupt:
        logger.info("\n\nShutting down gracefully...")
        db_session.close()
        logger.info("✓ Database connection closed")
        logger.info("Goodbye! 👋")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
