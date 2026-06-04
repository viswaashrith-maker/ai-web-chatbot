# Lazy initialization
client = None
collection = None


def _init_chroma():
    """Initialize Chroma client lazily on first use."""
    global client, collection

    if client is None:
        try:
            import chromadb

            client = chromadb.PersistentClient(
                path="./chroma_data"
            )

            collection = client.get_or_create_collection(
                name="chatbot_knowledge",
                metadata={"hnsw:space": "cosine"}
            )

        except ImportError as e:
            print(f"Warning: Chroma not available. RAG features disabled: {e}")
            return False

        except Exception as e:
            print(f"Error initializing Chroma: {e}")
            return False

    return True


def add_document(doc_id, content, metadata=None):
    """
    Add a document to the knowledge base.
    
    Args:
        doc_id: Unique identifier for the document
        content: Text content of the document
        metadata: Optional metadata dict
    """
    if not _init_chroma():
        print("Chroma not initialized, skipping document add")
        return
    
    if metadata is None:
        metadata = {}
    
    collection.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata]
    )


def add_documents_batch(documents_list):
    """
    Add multiple documents at once.
    
    Args:
        documents_list: List of dicts with keys: id, content, metadata (optional)
    """
    if not _init_chroma():
        return
    
    ids = []
    documents = []
    metadatas = []
    
    for doc in documents_list:
        ids.append(doc["id"])
        documents.append(doc["content"])
        metadatas.append(doc.get("metadata", {}))
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )


def retrieve_context(query, k=3):
    """
    Retrieve the top k most relevant documents for a query.
    
    Args:
        query: User query string
        k: Number of results to return (default 3)
    
    Returns:
        List of relevant document texts
    """
    if not _init_chroma():
        return []
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=k
        )
        
        if results and results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return []


def get_context_string(query, k=3):
    """
    Get formatted context string for LLM prompt.
    
    Args:
        query: User query string
        k: Number of results to return
    
    Returns:
        Formatted string with relevant context
    """
    docs = retrieve_context(query, k)
    
    if not docs:
        return ""
    
    context = "**Relevant Context:**\n"
    for i, doc in enumerate(docs, 1):
        context += f"{i}. {doc}\n"
    
    return context


def clear_knowledge_base():
    """Clear all documents from the collection."""
    if not _init_chroma():
        return
    
    try:
        client.delete_collection(name="chatbot_knowledge")
        global collection
        collection = client.get_or_create_collection(
            name="chatbot_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        print(f"Error clearing knowledge base: {e}")


def get_collection_count():
    """Get the number of documents in the collection."""
    if not _init_chroma():
        return 0
    
    try:
        return collection.count()
    except Exception as e:
        print(f"Error getting collection count: {e}")
        return 0
