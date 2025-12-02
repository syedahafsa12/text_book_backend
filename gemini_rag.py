import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from typing import List, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Gemini
genai.configure(api_key=settings.gemini_api_key)

# Initialize Qdrant
try:
    qdrant_client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
    logger.info("Connected to Qdrant Cloud")
except Exception as e:
    logger.warning(f"Qdrant connection failed: {e}. Using mock client.")
    class MockQdrantClient:
        def search(self, collection_name, query_vector, limit=3):
            return [
                qmodels.ScoredPoint(
                    id=1, 
                    version=1, 
                    score=0.9, 
                    payload={"text": "ROS 2 is a middleware framework for robotics..."}, 
                    vector=[]
                )
            ]
    qdrant_client = MockQdrantClient()

class GeminiRAG:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.embedding_model = 'models/text-embedding-004'
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return a dummy embedding if it fails
            return [0.0] * 768
    
    def search_context(self, query: str, limit: int = 3) -> List[str]:
        """Search for relevant context in Qdrant"""
        try:
            query_vector = self.generate_embedding(query)
            search_results = qdrant_client.search(
                collection_name="textbook_content",
                query_vector=query_vector,
                limit=limit
            )
            return [hit.payload.get("text", "") for hit in search_results]
        except Exception as e:
            logger.error(f"Context search failed: {e}")
            return ["ROS 2 is a middleware framework for robotics applications."]
    
    def generate_answer(
        self, 
        question: str, 
        context: List[str], 
        user_profile: Optional[dict] = None,
        language: str = "en"
    ) -> str:
        """Generate answer using Gemini with context and personalization"""
        
        # Build personalization context
        personalization = ""
        if user_profile:
            personalization = f"""
User Profile:
- Software Background: {user_profile.get('software_background', 'Unknown')}
- Hardware Background: {user_profile.get('hardware_background', 'Unknown')}
- Experience Level: {user_profile.get('experience_level', 'beginner')}
- OS: {user_profile.get('operating_system', 'Unknown')}

Adapt your answer to match the user's background and experience level.
"""
        
        # Build language instruction
        language_instruction = ""
        if language == "ur":
            language_instruction = "Please respond in Urdu (اردو) with proper RTL formatting."
        
        # Construct prompt
        context_text = "\n\n".join(context)
        prompt = f"""You are an AI assistant for a Physical AI & Humanoid Robotics textbook.

{personalization}

Context from the textbook:
{context_text}

{language_instruction}

User Question: {question}

Instructions:
1. Answer ONLY based on the provided context from the textbook
2. If the context doesn't contain the answer, say "I don't have enough information in the textbook to answer that."
3. Be concise but thorough
4. Use examples from the context when relevant
5. If personalization info is provided, adapt your explanation to the user's level

Answer:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"I apologize, but I encountered an error generating a response. Error: {str(e)}"
    
    def translate_to_urdu(self, text: str) -> str:
        """Translate text to Urdu"""
        prompt = f"""Translate the following text to Urdu (اردو). 
Maintain technical terms in English if they don't have common Urdu equivalents.
Use proper RTL formatting.

Text to translate:
{text}

Urdu Translation:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text
    
    def personalize_content(self, content: str, user_profile: dict) -> str:
        """Personalize content based on user profile"""
        prompt = f"""Adapt the following educational content for a user with this profile:
- Software Background: {user_profile.get('software_background', 'Unknown')}
- Hardware Background: {user_profile.get('hardware_background', 'Unknown')}
- Experience Level: {user_profile.get('experience_level', 'beginner')}

Original Content:
{content}

Instructions:
1. Adjust complexity to match experience level
2. Add relevant examples based on their background
3. Use analogies they would understand
4. Keep the same structure and key concepts

Personalized Content:"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Personalization failed: {e}")
            return content

# Global instance
gemini_rag = GeminiRAG()
