import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router";
import { Header } from "./components/Header";
import { DashboardProvider, ViewingAs, useDashboard } from "./components/HeaderTools";
import { ContainersPage } from "./pages/ContainersPage";
import { CostsPage } from "./pages/CostsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DataPage } from "./pages/DataPage";
import { DecisionsPage } from "./pages/DecisionsPage";
import { FeaturePage } from "./pages/FeaturePage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { OperatorsPage } from "./pages/OperatorsPage";
import { ValuePage } from "./pages/ValuePage";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/app.css";

function Footer() {
  return (
    <footer className="page footer">
      <span />
      <ViewingAs />
      <span className="footer-links">
        <Link to="/data" className="footer-link">
          About the data
        </Link>
      </span>
    </footer>
  );
}

function Feature({ title, path }: { title: string; path: string }) {
  return <FeaturePage title={title} endpoint={path} />;
}

function Main() {
  const { version } = useDashboard();
  return (
    <main className="page" key={version}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/costs" element={<CostsPage />} />
        <Route path="/operators" element={<OperatorsPage />} />
        <Route path="/pickups" element={<Feature title="Pickups" path="/api/pickups" />} />
        <Route path="/site-checks" element={<Feature title="Site checks" path="/api/site-checks" />} />
        <Route path="/fleet" element={<Feature title="Fleet & Scales" path="/api/fleet" />} />
        <Route path="/containers" element={<ContainersPage />} />
        <Route path="/value" element={<ValuePage />} />
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/data" element={<DataPage />} />
        <Route path="*" element={<DashboardPage />} />
      </Routes>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <DashboardProvider>
        <Header />
        <Main />
        <Footer />
      </DashboardProvider>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
