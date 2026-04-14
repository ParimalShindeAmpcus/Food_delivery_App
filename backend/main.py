from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import uvicorn

from db import (
    close_db,
    get_restaurant as db_get_restaurant,
    get_restaurants as db_get_restaurants,
    init_db,
    save_order,
)

# Load environment variables
load_dotenv()

app = FastAPI(title="Foodie Feed Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event() -> None:
    await init_db()

@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_db()

# Initialize Groq client
groq_available = bool(os.getenv("GROQ_API_KEY"))
if groq_available:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    groq_model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    print(f"🤖 Groq AI integration enabled (model: {groq_model})")
else:
    groq_client = None
    groq_model = "mixtral-8x7b-32768"
    print("⚠️  Groq API key not found. Using fallback rule-based AI.")


class MenuItem(BaseModel):
    id: str
    name: str
    description: str
    price: float
    image: str
    category: str
    isVeg: bool
    isBestseller: bool | None = None


class Restaurant(BaseModel):
    id: str
    name: str
    image: str
    cuisine: List[str]
    rating: float
    deliveryTime: str
    priceRange: str
    distance: str
    featured: bool | None = None
    menu: List[MenuItem]


class Customer(BaseModel):
    name: str
    address: str
    phone: str
    paymentMethod: str


class OrderItem(BaseModel):
    menuItem: MenuItem
    quantity: int


class OrderRequest(BaseModel):
    items: List[OrderItem]
    customer: Customer
    total: float
    restaurantId: str


class OrderResponse(BaseModel):
    orderId: str
    estimatedTime: str


class SearchFilters(BaseModel):
    category: Optional[str] = None
    max_price: Optional[float] = None
    veg: Optional[bool] = None
    spice_level: Optional[str] = None
    cuisine: Optional[str] = None


class IntentResponse(BaseModel):
    intent: str


class RecommendationResponse(BaseModel):
    recommendations: List[str]


class ChatResponse(BaseModel):
    response: str


class QueryRequest(BaseModel):
    query: str


class HistoryRequest(BaseModel):
    history: List[Dict[str, Any]]


def parse_search_query(query: str) -> Dict[str, Any]:
    """Parse natural language query into structured filters using Groq or fallback."""
    if not groq_available or not groq_client:
        return parse_search_query_fallback(query)

    try:
        prompt = f"""
You are a food search query parser for a food delivery app.

Convert the user's natural language query into structured JSON filters.

Available cuisines: Indian, Chinese, Italian, Japanese, American, Thai, Mediterranean, Pizza, Burgers, Sushi
Available categories: Pizza, Burger, Biryani, Pasta, Sushi, Curry, Salad, Dessert, Main Course, Starters, Breads, Sides, Drinks, Wraps, Soups, Nigiri

Rules:
- Return ONLY valid JSON
- Extract relevant filters like: category, max_price, veg (true/false), spice_level (low/medium/high), cuisine
- If no specific filter mentioned, set to null
- Be flexible with synonyms (e.g., "vegetarian" = veg: true, "cheap" = reasonable max_price)

Example:
Input: "cheap veg pizza under 200"
Output: {{"category": "pizza", "max_price": 200, "veg": true, "spice_level": null, "cuisine": null}}

Now process this query: "{query}"
"""

        response = groq_client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )

        result = response.choices[0].message.content.strip()

        # Try to parse as JSON
        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError:
            # Fallback to basic parsing if AI returns invalid JSON
            return parse_search_query_fallback(query)

    except Exception as e:
        print(f"Groq search parsing failed: {e}")
        # Fallback to rule-based parsing
        return parse_search_query_fallback(query)


def parse_search_query_fallback(query: str) -> Dict[str, Any]:
    """Fallback rule-based search parsing."""
    filters = {
        "category": None,
        "max_price": None,
        "veg": None,
        "spice_level": None,
        "cuisine": None
    }

    query_lower = query.lower()

    # Extract price
    price_match = re.search(r'under\s+(\d+)', query_lower)
    if price_match:
        filters["max_price"] = float(price_match.group(1))

    # Extract veg/non-veg
    if 'veg' in query_lower or 'vegetarian' in query_lower:
        filters["veg"] = True
    elif 'non-veg' in query_lower or 'non veg' in query_lower:
        filters["veg"] = False

    # Extract cuisine
    cuisines = ['indian', 'chinese', 'italian', 'japanese', 'american', 'thai', 'mediterranean']
    for cuisine in cuisines:
        if cuisine in query_lower:
            filters["cuisine"] = cuisine
            break

    # Extract category
    categories = ['pizza', 'burger', 'biryani', 'pasta', 'sushi', 'curry', 'salad', 'dessert']
    for category in categories:
        if category in query_lower:
            filters["category"] = category
            break

    # Extract spice level
    if 'spicy' in query_lower or 'hot' in query_lower:
        filters["spice_level"] = "high"
    elif 'mild' in query_lower:
        filters["spice_level"] = "low"

    return filters


def detect_intent(query: str) -> str:
    """Detect user intent from query using Groq or fallback."""
    if not groq_available or not groq_client:
        return detect_intent_fallback(query)

    try:
        prompt = f"""
Classify the user's intent from their food delivery query.

Possible intents:
- search_food: Looking for restaurants or food items
- place_order: Ready to order or asking about ordering
- ask_recommendation: Asking for suggestions or recommendations
- general_question: General questions about food, delivery, etc.

Return ONLY the intent name.

User query: "{query}"
"""

        response = groq_client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )

        intent = response.choices[0].message.content.strip().lower()

        valid_intents = ["search_food", "place_order", "ask_recommendation", "general_question"]
        if intent in valid_intents:
            return intent
        else:
            return "general_question"

    except Exception as e:
        print(f"Groq intent detection failed: {e}")
        return detect_intent_fallback(query)


def detect_intent_fallback(query: str) -> str:
    """Fallback rule-based intent detection."""
    query_lower = query.lower()

    if any(word in query_lower for word in ['find', 'search', 'looking for', 'want']):
        return "search_food"
    elif any(word in query_lower for word in ['order', 'place', 'buy', 'get']):
        return "place_order"
    elif any(word in query_lower for word in ['recommend', 'suggest', 'what should i']):
        return "ask_recommendation"
    else:
        return "general_question"


def generate_recommendations(history: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on order history using Groq or fallback."""
    if not groq_available or not groq_client:
        return generate_recommendations_fallback(history)

    try:
        history_text = json.dumps(history, indent=2)

        prompt = f"""
You are a food recommendation engine for a food delivery app.

Based on the user's past orders, suggest 3 food items they might like.

User's order history:
{history_text}

Available restaurants and menu items:
- The Spice Garden: Indian cuisine (Butter Chicken, Paneer Tikka, Dal Makhani, etc.)
- Pizza Paradise: Italian/Pizza (Margherita Pizza, Pepperoni Pizza, Caesar Salad, etc.)
- Sushi Sensation: Japanese/Sushi (California Roll, Salmon Nigiri, Edamame, etc.)
- Burger Barn: American/Burgers (Classic Cheeseburger, Veggie Burger, Loaded Fries, etc.)
- Thai Orchid: Thai/Asian (Pad Thai, Green Curry, Spring Rolls, etc.)
- Mediterranean Bites: Mediterranean/Greek (Falafel Wrap, Chicken Shawarma, Greek Salad, etc.)

Rules:
- Suggest items from existing restaurants
- Consider user's past preferences (cuisine, veg/non-veg, etc.)
- Mix familiar items with new suggestions
- Return exactly 3 recommendations as a JSON array of strings
- Keep suggestions realistic and appealing

Return ONLY a JSON array like: ["Butter Chicken", "Margherita Pizza", "Falafel Wrap"]
"""

        response = groq_client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        try:
            recommendations = json.loads(result)
            if isinstance(recommendations, list) and len(recommendations) >= 3:
                return recommendations[:3]
        except json.JSONDecodeError:
            pass

        # Fallback recommendations
        return generate_recommendations_fallback(history)

    except Exception as e:
        print(f"Groq recommendations failed: {e}")
        return generate_recommendations_fallback(history)


def generate_recommendations_fallback(history: List[Dict[str, Any]]) -> List[str]:
    """Fallback rule-based recommendations."""
    if not history:
        return ["Margherita Pizza", "Paneer Tikka", "Caesar Salad"]

    # Simple logic: recommend popular items from same cuisine
    ordered_items = []
    for order in history:
        for item in order.items:
            ordered_items.append(item.menuItem.name)

    # Mock recommendations based on history
    recommendations = []
    if any('pizza' in item.lower() for item in ordered_items):
        recommendations.extend(["Pepperoni Pizza", "Pasta Carbonara"])
    if any('indian' in item.lower() for item in ordered_items):
        recommendations.extend(["Chicken Biryani", "Butter Chicken"])
    if any('sushi' in item.lower() for item in ordered_items):
        recommendations.extend(["California Roll", "Salmon Nigiri"])

    # Fallback recommendations
    if len(recommendations) < 3:
        recommendations.extend(["Classic Cheeseburger", "Falafel Wrap", "Tiramisu"])

    return recommendations[:3]


def generate_chat_response(query: str, intent: str) -> str:
    """Generate helpful chat response using Groq or fallback."""
    if not groq_available or not groq_client:
        return generate_chat_response_fallback(query, intent)

    try:
        context = f"""
You are an AI assistant inside a food delivery app called BiteRush.

Your job is to help users:
- find food and restaurants
- suggest dishes based on preferences
- filter menu items
- assist in ordering
- answer questions about food delivery

User query: "{query}"
Detected intent: {intent}

Rules:
- Always be concise and helpful (max 2-3 sentences)
- Prefer suggesting actual food items over generic advice
- If user gives preferences (price, veg/non-veg, spicy, cuisine), use them
- If unclear, ask a short follow-up question
- Do NOT hallucinate items not in menu
- Keep responses short and actionable

Available restaurants:
- The Spice Garden (Indian): Butter Chicken, Paneer Tikka, Chicken Biryani
- Pizza Paradise (Italian): Margherita Pizza, Pepperoni Pizza, Pasta Carbonara
- Sushi Sensation (Japanese): California Roll, Salmon Nigiri, Edamame
- Burger Barn (American): Classic Cheeseburger, Veggie Burger, Loaded Fries
- Thai Orchid (Thai): Pad Thai, Green Curry, Mango Sticky Rice
- Mediterranean Bites (Mediterranean): Falafel Wrap, Chicken Shawarma, Greek Salad

Generate a helpful response:
"""

        response = groq_client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": context}],
            temperature=0.7,
            max_tokens=200
        )

        ai_response = response.choices[0].message.content.strip()
        return ai_response

    except Exception as e:
        print(f"Groq chat failed: {e}")
        return generate_chat_response_fallback(query, intent)


def generate_chat_response_fallback(query: str, intent: str) -> str:
    """Fallback rule-based chat response."""
    if intent == "search_food":
        return "I can help you find food! Try searching for 'veg pizza under 200' or tell me what you're craving."
    elif intent == "place_order":
        return "Ready to place an order? Browse restaurants and add items to your cart."
    elif intent == "ask_recommendation":
        return "Based on popular choices, I'd recommend Margherita Pizza, Paneer Tikka, and Caesar Salad."
    else:
        return "I'm here to help with food delivery! Ask me about restaurants, menus, or recommendations."


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/restaurants", response_model=List[Restaurant])
async def get_restaurants():
    return await db_get_restaurants()


@app.get("/api/restaurants/{restaurant_id}", response_model=Restaurant)
async def get_restaurant(restaurant_id: str):
    restaurant = await db_get_restaurant(restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@app.post("/api/orders", response_model=OrderResponse, status_code=201)
async def place_order(order: OrderRequest):
    if not order.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    order_id = f"ORD-{int(datetime.utcnow().timestamp() * 1000)}"
    order_data = {
        "id": order_id,
        "items": [
            {
                "menuItem": item.menuItem.dict(),
                "quantity": item.quantity,
            }
            for item in order.items
        ],
        "customer": order.customer.dict(),
        "total": order.total,
        "restaurantId": order.restaurantId,
        "estimatedTime": "30-45 min",
        "createdAt": datetime.utcnow().isoformat(),
    }

    await save_order(order_data)
    return {"orderId": order_id, "estimatedTime": "30-45 min"}


@app.post("/api/ai/search", response_model=SearchFilters)
async def ai_search(request: QueryRequest):
    """Parse natural language search query into filters."""
    return parse_search_query(request.query)


@app.post("/api/ai/intent", response_model=IntentResponse)
async def ai_intent(request: QueryRequest):
    """Detect user intent from query."""
    intent = detect_intent(request.query)
    return {"intent": intent}


@app.post("/api/ai/recommend", response_model=RecommendationResponse)
async def ai_recommend(request: HistoryRequest):
    """Generate recommendations based on order history."""
    recommendations = generate_recommendations(request.history)
    return {"recommendations": recommendations}


@app.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(request: QueryRequest):
    """Generate helpful chat response."""
    intent = detect_intent(request.query)
    response = generate_chat_response(request.query, intent)
    return {"response": response}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=4000, reload=True)
