import os
import chromadb
import torch
from transformers import AutoTokenizer, AutoModel

# Initialize the local persistent client
DB_DIR = "memory/db"
os.makedirs(DB_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=DB_DIR)

# Get or create the vector collection
collection = client.get_or_create_collection(
    name="friday_memory"
)

# Configure HuggingFace cache directory inside the models directory
CACHE_DIR = "models/hf_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class OfflineEmbeddingModel:
    """
    Offline Sentence Embedding Generator using standard transformers library.
    Generates high-quality 384-dimensional sentence embeddings using mean pooling.
    """
    def __init__(self):
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        # Download once (if needed) and run fully offline afterwards
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=CACHE_DIR)
        self.model = AutoModel.from_pretrained(model_name, cache_dir=CACHE_DIR)
        self.model.eval()

    def encode(self, text: str) -> list:
        # Tokenize and format inputs
        inputs = self.tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Perform mean pooling to obtain sentence representation
        token_embeddings = outputs[0]
        attention_mask = inputs['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        sentence_embedding = sum_embeddings / sum_mask
        
        return sentence_embedding[0].tolist()

# Load the local lightweight embedding model
try:
    model = OfflineEmbeddingModel()
except Exception as e:
    print(f"[Warning] Could not load offline embedding model: {e}")
    model = None


def store_memory(text, metadata=None):
    """
    Encodes text into a dense vector embedding and adds it to the ChromaDB collection.
    """
    if model is None:
        return
        
    try:
        embedding = model.encode(text)
        doc_id = str(hash(text))
        
        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None,
            ids=[doc_id]
        )
    except Exception as e:
        print(f"[Warning] Error storing persistent memory: {e}")


def search_memory(query):
    """
    Queries ChromaDB with semantic search embeddings to find top 3 relevant historical context turns.
    """
    if model is None:
        return []
        
    try:
        embedding = model.encode(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=3
        )
        
        # Return standard flat list of matched documents
        if results and "documents" in results and results["documents"]:
            return results["documents"][0]
    except Exception as e:
        print(f"[Warning] Error querying persistent memory: {e}")
        
    return []

