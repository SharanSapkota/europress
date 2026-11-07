import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router";
import { CostsPage } from "./pages/CostsPage";
import { DataPage } from "./pages/DataPage";
import { DecisionsPage } from "./pages/DecisionsPage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { OperatorsPage } from "./pages/OperatorsPage";
import { PrimaryIdeasPage } from "./pages/PrimaryIdeasPage";
import { SecondaryIdeasPage } from "./pages/SecondaryIdeasPage";
import "./styles/tokens.css";
import "./styles/app.css";

function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <span className="brand">Smart Weight</span>
        <nav aria-label="Main" className="nav">
          <NavLink to="/" end className="nav-link">
            Invoices
          </NavLink>
          <NavLink to="/costs" className="nav-link">
            Cost per tonne
          </NavLink>
          <NavLink to="/operators" className="nav-link">
            Operators
          </NavLink>
          <NavLink to="/primary-ideas" className="nav-link">
            Primary ideas (5, 3, 6)
          </NavLink>
          <NavLink to="/secondary-ideas" className="nav-link">
            Secondary ideas &amp; Task D
          </NavLink>
        </nav>
      </header>
      <main className="page">
        <Routes>
          <Route path="/costs" element={<CostsPage />} />
          <Route path="/operators" element={<OperatorsPage />} />
          <Route path="/primary-ideas" element={<PrimaryIdeasPage />} />
          <Route path="/secondary-ideas" element={<SecondaryIdeasPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="*" element={<InvoicesPage />} />
        </Routes>
      </main>
      <footer className="page footer">
        <span>Our amounts are estimates. Demo data.</span>
        <span className="footer-links">
          <Link to="/data" className="footer-link">
            About the data
          </Link>
          <Link to="/decisions" className="footer-link">
            Decisions
          </Link>
        </span>
      </footer>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
