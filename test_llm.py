import sys
print("Python version:", sys.version)

try:
    from sentence_transformers import SentenceTransformer
    print("sentence_transformers imported")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Model loaded")
    embedding = model.encode("test sentence")
    print(f"Embedding shape: {embedding.shape}")
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")