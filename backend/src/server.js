import cors from "cors";
import express from "express";
import morgan from "morgan";
import { restaurants } from "./data.js";

const app = express();
const port = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());
app.use(morgan("dev"));

const orders = [];

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", uptime: process.uptime() });
});

app.get("/api/restaurants", (_req, res) => {
  res.json(restaurants);
});

app.get("/api/restaurants/:id", (req, res) => {
  const restaurant = restaurants.find((item) => item.id === req.params.id);

  if (!restaurant) {
    return res.status(404).json({ message: "Restaurant not found" });
  }

  res.json(restaurant);
});

app.post("/api/orders", (req, res) => {
  const { items, customer, total, restaurantId } = req.body;

  if (
    !Array.isArray(items) ||
    items.length === 0 ||
    !customer ||
    !customer.name ||
    !customer.address ||
    !customer.phone ||
    !customer.paymentMethod ||
    typeof total !== "number" ||
    !restaurantId
  ) {
    return res.status(400).json({ message: "Invalid order payload" });
  }

  const order = {
    id: `ORD-${Date.now().toString(36).toUpperCase()}`,
    items,
    customer,
    total,
    restaurantId,
    estimatedTime: "30-45 min",
    createdAt: new Date().toISOString(),
  };

  orders.push(order);

  res.status(201).json({ orderId: order.id, estimatedTime: order.estimatedTime });
});

app.use((req, res) => {
  res.status(404).json({ message: "Endpoint not found" });
});

app.listen(port, () => {
  console.log(`Foodie Feed backend listening on http://localhost:${port}`);
});
