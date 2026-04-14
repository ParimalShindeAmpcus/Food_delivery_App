import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/foodie_feed",
)

pool: Optional[asyncpg.pool.Pool] = None
db_available = False

async def init_db() -> None:
    global pool, db_available
    # Force use static data for now
    db_available = False
    print("Using static data fallback")

async def create_tables(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            image TEXT,
            cuisine JSONB,
            rating REAL,
            delivery_time TEXT,
            price_range TEXT,
            distance TEXT,
            featured BOOLEAN DEFAULT FALSE
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id TEXT PRIMARY KEY,
            restaurant_id TEXT REFERENCES restaurants(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            image TEXT,
            category TEXT,
            is_veg BOOLEAN,
            is_bestseller BOOLEAN DEFAULT FALSE
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            restaurant_id TEXT REFERENCES restaurants(id),
            customer JSONB,
            items JSONB,
            total REAL,
            estimated_time TEXT,
            created_at TIMESTAMPTZ
        )
        """
    )

async def seed_sample_data(conn: asyncpg.Connection) -> None:
    from seed_data import RESTAURANTS

    async with conn.transaction():
        for restaurant in RESTAURANTS:
            await conn.execute(
                """
                INSERT INTO restaurants (id, name, image, cuisine, rating, delivery_time, price_range, distance, featured)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    image = EXCLUDED.image,
                    cuisine = EXCLUDED.cuisine,
                    rating = EXCLUDED.rating,
                    delivery_time = EXCLUDED.delivery_time,
                    price_range = EXCLUDED.price_range,
                    distance = EXCLUDED.distance,
                    featured = EXCLUDED.featured
                """,
                restaurant["id"],
                restaurant["name"],
                restaurant["image"],
                json.dumps(restaurant["cuisine"]),
                restaurant.get("rating"),
                restaurant.get("deliveryTime"),
                restaurant.get("priceRange"),
                restaurant.get("distance"),
                restaurant.get("featured", False),
            )

            for menu_item in restaurant.get("menu", []):
                await conn.execute(
                    """
                    INSERT INTO menu_items (
                        id,
                        restaurant_id,
                        name,
                        description,
                        price,
                        image,
                        category,
                        is_veg,
                        is_bestseller
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        restaurant_id = EXCLUDED.restaurant_id,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        price = EXCLUDED.price,
                        image = EXCLUDED.image,
                        category = EXCLUDED.category,
                        is_veg = EXCLUDED.is_veg,
                        is_bestseller = EXCLUDED.is_bestseller
                    """,
                    menu_item["id"],
                    restaurant["id"],
                    menu_item["name"],
                    menu_item.get("description"),
                    menu_item.get("price"),
                    menu_item.get("image"),
                    menu_item.get("category"),
                    menu_item.get("isVeg", False),
                    menu_item.get("isBestseller", False),
                )

async def get_restaurants() -> List[Dict[str, Any]]:
    print(f"get_restaurants: db_available = {db_available}")
    if not db_available:
        try:
            from data import restaurants
            print(f"Using static data: {len(restaurants)} restaurants")
            return restaurants
        except Exception as e:
            print(f"Error importing static data: {e}")
            return []

    assert pool is not None, "Database pool is not initialized"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.id AS restaurant_id,
                   r.name,
                   r.image,
                   r.cuisine,
                   r.rating,
                   r.delivery_time,
                   r.price_range,
                   r.distance,
                   r.featured,
                   m.id AS menu_id,
                   m.name AS menu_name,
                   m.description AS menu_description,
                   m.price AS menu_price,
                   m.image AS menu_image,
                   m.category AS menu_category,
                   m.is_veg AS menu_is_veg,
                   m.is_bestseller AS menu_is_bestseller
            FROM restaurants r
            LEFT JOIN menu_items m ON m.restaurant_id = r.id
            ORDER BY r.id, m.name
            """
        )

        restaurants: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            restaurant_id = row["restaurant_id"]
            if restaurant_id not in restaurants:
                restaurants[restaurant_id] = {
                    "id": restaurant_id,
                    "name": row["name"],
                    "image": row["image"],
                    "cuisine": row["cuisine"],
                    "rating": row["rating"],
                    "deliveryTime": row["delivery_time"],
                    "priceRange": row["price_range"],
                    "distance": row["distance"],
                    "featured": row["featured"],
                    "menu": [],
                }

            if row["menu_id"]:
                restaurants[restaurant_id]["menu"].append(
                    {
                        "id": row["menu_id"],
                        "name": row["menu_name"],
                        "description": row["menu_description"],
                        "price": row["menu_price"],
                        "image": row["menu_image"],
                        "category": row["menu_category"],
                        "isVeg": row["menu_is_veg"],
                        "isBestseller": row["menu_is_bestseller"],
                    }
                )

        return list(restaurants.values())

async def get_restaurant(restaurant_id: str) -> Optional[Dict[str, Any]]:
    if not db_available:
        from data import restaurants
        return next((r for r in restaurants if r["id"] == restaurant_id), None)

    assert pool is not None, "Database pool is not initialized"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.id AS restaurant_id,
                   r.name,
                   r.image,
                   r.cuisine,
                   r.rating,
                   r.delivery_time,
                   r.price_range,
                   r.distance,
                   r.featured,
                   m.id AS menu_id,
                   m.name AS menu_name,
                   m.description AS menu_description,
                   m.price AS menu_price,
                   m.image AS menu_image,
                   m.category AS menu_category,
                   m.is_veg AS menu_is_veg,
                   m.is_bestseller AS menu_is_bestseller
            FROM restaurants r
            LEFT JOIN menu_items m ON m.restaurant_id = r.id
            WHERE r.id = $1
            ORDER BY m.name
            """,
            restaurant_id,
        )

        if not rows:
            return None

        restaurant = {
            "id": rows[0]["restaurant_id"],
            "name": rows[0]["name"],
            "image": rows[0]["image"],
            "cuisine": rows[0]["cuisine"],
            "rating": rows[0]["rating"],
            "deliveryTime": rows[0]["delivery_time"],
            "priceRange": rows[0]["price_range"],
            "distance": rows[0]["distance"],
            "featured": rows[0]["featured"],
            "menu": [],
        }

        for row in rows:
            if row["menu_id"]:
                restaurant["menu"].append(
                    {
                        "id": row["menu_id"],
                        "name": row["menu_name"],
                        "description": row["menu_description"],
                        "price": row["menu_price"],
                        "image": row["menu_image"],
                        "category": row["menu_category"],
                        "isVeg": row["menu_is_veg"],
                        "isBestseller": row["menu_is_bestseller"],
                    }
                )

        return restaurant

async def save_order(order: Dict[str, Any]) -> None:
    if not db_available:
        print(f"📝 Order saved (fallback mode): {order['id']}")
        return

    assert pool is not None, "Database pool is not initialized"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO orders (
                id,
                restaurant_id,
                customer,
                items,
                total,
                estimated_time,
                created_at
            ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7)
            """,
            order["id"],
            order["restaurantId"],
            json.dumps(order["customer"]),
            json.dumps(order["items"]),
            order["total"],
            order["estimatedTime"],
            order["createdAt"],
        )

async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None
