"""
Content Ingestion Script for Qdrant
This script reads all Markdown files from docs/ and ingests them into Qdrant
"""

import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from dotenv import load_dotenv
import re
from pathlib import Path

load_dotenv()

# Initialize
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

COLLECTION_NAME = "textbook_content"
EMBEDDING_MODEL = 'models/text-embedding-004'

def chunk_text(text, chunk_size=500):
    """Split text into chunks of approximately chunk_size words"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        current_chunk.append(word)
        current_size += 1
        
        if current_size >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def clean_markdown(text):
    """Remove markdown syntax for cleaner text"""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]*`', '', text)
    # Remove links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove headers
    text = re.sub(r'#+\s+', '', text)
    # Remove bold/italic
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    return text.strip()

def generate_embedding(text):
    """Generate embedding using Gemini"""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def ingest_docs():
    """Read all docs and ingest into Qdrant"""
    
    print("🚀 Starting content ingestion...")
    
    # Create collection
    try:
        qdrant_client.delete_collection(COLLECTION_NAME)
        print("🗑️  Deleted existing collection")
    except:
        pass
    
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=768,  # Gemini embedding size
            distance=qmodels.Distance.COSINE
        )
    )
    print("✅ Created collection")
    
    # Find all markdown files
    docs_path = Path("../website/docs")
    md_files = list(docs_path.rglob("*.md"))
    
    print(f"📚 Found {len(md_files)} markdown files")
    
    points = []
    point_id = 0
    
    for md_file in md_files:
        print(f"📖 Processing: {md_file.name}")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove frontmatter
        content = re.sub(r'^---[\s\S]*?---\n', '', content)
        
        # Clean and chunk
        clean_content = clean_markdown(content)
        chunks = chunk_text(clean_content, chunk_size=400)
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very small chunks
                continue
            
            try:
                embedding = generate_embedding(chunk)
                
                points.append(qmodels.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "source": str(md_file.relative_to(docs_path)),
                        "chunk_index": i
                    }
                ))
                
                point_id += 1
                
                if len(points) >= 10:  # Batch upload
                    qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=points
                    )
                    print(f"  ✅ Uploaded {len(points)} chunks")
                    points = []
                
            except Exception as e:
                print(f"  ❌ Error processing chunk: {e}")
    
    # Upload remaining points
    if points:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"✅ Uploaded final {len(points)} chunks")
    
    # Get collection info
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"\n🎉 Ingestion complete!")
    print(f"📊 Total vectors: {collection_info.points_count}")

if __name__ == "__main__":
    print("=" * 50)
    print("Content Ingestion for RAG System")
    print("=" * 50)
    print()
    
    try:
        ingest_docs()
        print("\n✅ Success! Your chatbot now has full textbook context.")
        print("🤖 Try asking: 'What is Physical AI?'")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check QDRANT_URL and QDRANT_API_KEY in .env")
        print("2. Verify Qdrant cluster is running")
        print("3. Check GEMINI_API_KEY is valid")
