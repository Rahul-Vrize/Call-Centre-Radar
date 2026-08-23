import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

// TODO: typed wrappers matching backend/app/schemas/call.py
// e.g. getCustomers(), getCustomerCalls(id), getCall(id), getAttention(date),
// getTrends(), getAgents()
