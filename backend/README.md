# Foodie Feed Backend

This backend is built with FastAPI and exposes a REST API for the Foodie Feed frontend. It includes AI-powered features using **Groq's free AI models** (Mixtral, Llama2, Gemma).

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m pip install -r requirements.txt
```

### 2. Configure PostgreSQL

1. Install PostgreSQL and open pgAdmin.
2. Create a database named `foodie_feed`.
3. Create a user with a password, or use the default `postgres` user.
4. Copy the connection string into `backend/.env`:

```bash
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/foodie_feed
```

### 3. Configure Groq API (Free)

1. Get your free Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys)
2. Edit `.env` file:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Then restart the backend after changing `.env` so the new model and key are loaded.

**Available Groq Models (all free tier):**
- `mixtral-8x7b-32768` (recommended, fast and powerful) ⭐
- `llama2-70b-4096` (good for recommendations)
- `gemma-7b-it` (fastest, smallest)

### 3. Run the Backend

Use PostgreSQL via pgAdmin, then start the FastAPI backend with Uvicorn:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 4000 --reload
```

Or run directly with Python if you prefer:

```bash
cd backend
python main.py
```

The backend listens on `http://localhost:4000` by default.

## Testing AI Features

After setting up your Groq API key, test the AI endpoints:

```bash
cd backend
python test_ai.py
```

## API

### Core Endpoints
- `GET /api/health` - health check
- `GET /api/restaurants` - get all restaurants
- `GET /api/restaurants/{id}` - get restaurant details
- `POST /api/orders` - place a new order

### AI Endpoints (Powered by Groq - Free!)
- `POST /api/ai/search` - parse natural language search query into filters
- `POST /api/ai/intent` - detect user intent from query
- `POST /api/ai/recommend` - generate recommendations based on order history
- `POST /api/ai/chat` - generate helpful chat response

## AI Features

The backend uses Groq's free AI models for:

1. **Smart Search Parsing**: Converts natural language queries like "cheap veg pizza under 200" into structured filters
2. **Intent Detection**: Classifies user queries (search, order, recommend, general questions)
3. **Personalized Recommendations**: Suggests food items based on order history
4. **Conversational AI**: Provides helpful responses about food delivery and restaurant information

### Why Groq?

✅ **Completely Free** - No cost, ever  
✅ **Fast** - Fastest AI inference available  
✅ **Powerful Models** - Mixtral (8x7B) is excellent quality  
✅ **No Rate Limits** - Generous free tier  
✅ **Easy Integration** - OpenAI-compatible API  

## Environment Variables

- `GROQ_API_KEY` - Your Groq API key (required, get it free from https://console.groq.com/keys)
- `GROQ_MODEL` - Model to use (optional, defaults to `mixtral-8x7b-32768`)
- `DATABASE_URL` - PostgreSQL connection string for pgAdmin/backend

## Notes

- Restaurant and order data are now persisted in PostgreSQL instead of runtime memory.
- Sample restaurant data will be seeded automatically when the database is empty.
- The backend includes fallback rule-based AI if Groq API fails.
- The backend is intentionally simple and suitable for local development.
