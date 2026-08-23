import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import CustomerList from "./pages/CustomerList";
import CustomerDetail from "./pages/CustomerDetail";
import CallDetail from "./pages/CallDetail";
import AttentionDashboard from "./pages/AttentionDashboard";
import TrendsDashboard from "./pages/TrendsDashboard";
import AgentsDashboard from "./pages/AgentsDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <nav className="flex gap-4 p-4 border-b">
        <Link to="/">Attention</Link>
        <Link to="/customers">Customers</Link>
        <Link to="/trends">Trends</Link>
        <Link to="/agents">Agents</Link>
      </nav>
      <Routes>
        <Route path="/" element={<AttentionDashboard />} />
        <Route path="/customers" element={<CustomerList />} />
        <Route path="/customers/:customerId" element={<CustomerDetail />} />
        <Route path="/calls/:callId" element={<CallDetail />} />
        <Route path="/trends" element={<TrendsDashboard />} />
        <Route path="/agents" element={<AgentsDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
