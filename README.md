# Physical AI & Humanoid Robotics - Backend

Production-ready FastAPI backend with Better-Auth, Gemini 2.0 Flash RAG, Qdrant Cloud, and Neon Postgres.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Neon Postgres account (free tier)
- Qdrant Cloud account (free tier)
- Gemini API key

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: From Neon Postgres
- `QDRANT_URL`: From Qdrant Cloud
- `QDRANT_API_KEY`: From Qdrant Cloud
- `GEMINI_API_KEY`: Your Gemini API key
- `BETTER_AUTH_SECRET`: Generate with `openssl rand -base64 32`

### 3. Initialize Database
```bash
# Connect to your Neon database and run:
psql $DATABASE_URL < init_db.sql
```

Or use a PostgreSQL client to execute `init_db.sql`.

### 4. Run the Server
```bash
python main.py
```

Server will start at `http://localhost:8000`

## 📚 API Documentation

### Authentication Endpoints

#### POST `/api/auth/signup`
Create a new user account with profile.

**Request:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "secure_password",
  "software_background": "Python",
  "hardware_background": "Arduino",
  "operating_system": "Ubuntu",
  "gpu_hardware": "NVIDIA RTX 3060"
}
```

**Response:**
```json
{
  "session_token": "eyJ...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### POST `/api/auth/signin`
Sign in with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

#### GET `/api/auth/me`
Get current user profile.

**Headers:**
```
Authorization: Bearer <session_token>
```

### RAG Endpoints

#### POST `/api/ask`
Ask a question to the AI assistant.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request:**
```json
{
  "question": "What is ROS 2?",
  "selected_text": "optional context",
  "language": "en"
}
```

**Response:**
```json
{
  "answer": "ROS 2 is...",
  "sources": ["Textbook Content"]
}
```

#### POST `/api/personalize`
Personalize content based on user profile.

**Request:**
```json
{
  "content": "Original chapter content..."
}
```

#### POST `/api/translate`
Translate content to Urdu.

**Request:**
```json
{
  "content": "Content to translate..."
}
```

## 🗄️ Database Schema

### Tables
- `users`: User accounts (Better-Auth compatible)
- `sessions`: Active sessions
- `user_profiles`: User background and preferences
- `chat_messages`: Chat history

See `init_db.sql` for complete schema.

## 🧠 Gemini RAG System

### Features
- **Embedding Generation**: Using `text-embedding-004`
- **Vector Search**: Qdrant Cloud integration
- **Personalized Responses**: Based on user profile
- **Multi-language**: English and Urdu support
- **Context-aware**: Uses selected text as additional context

### Configuration
The RAG system automatically:
1. Generates embeddings for user questions
2. Searches Qdrant for relevant context
3. Constructs personalized prompts
4. Generates answers using Gemini 2.0 Flash

## 🚢 Deployment

### Railway
1. Create new project on Railway
2. Add PostgreSQL plugin (or use Neon)
3. Add environment variables
4. Deploy from GitHub

### Render
1. Create new Web Service
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Docker
```bash
docker build -t textbook-backend .
docker run -p 8000:8000 --env-file .env textbook-backend
```

## 🔧 Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8 .
```

## 📝 Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Neon Postgres connection string | `postgresql://user:pass@ep-xxx.neon.tech/db` |
| `QDRANT_URL` | Qdrant Cloud cluster URL | `https://xxx.qdrant.io` |
| `QDRANT_API_KEY` | Qdrant API key | `your_key_here` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `BETTER_AUTH_SECRET` | Secret for JWT signing | Generate with openssl |
| `FRONTEND_URL` | Frontend URL for CORS | `http://localhost:3000` |

## 🐛 Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is correct
- Check if Neon database is active
- Ensure SSL mode is enabled

### Qdrant Connection Issues
- Verify cluster is running
- Check API key permissions
- Ensure collection exists

### Gemini API Issues
- Verify API key is valid
- Check quota limits
- Ensure model name is correct (`gemini-2.0-flash`)

## 📄 License
MIT
