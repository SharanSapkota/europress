import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { request, scope, type Why } from "../api/invoices";

export interface Tile {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  signed: boolean;
  status: "OK" | "CHECK";
  link: string;
}

export interface NextDecision {
  id: string;
  sentence: string;
  estimate: string;
  link: string;
  value_cents: number;
}

export interface Dashboard {
  customer_id: string;
  customer_name: string | null;
  sites: { id: string; name: string }[];
  operator_count: number;
  period: string | null;
  periods: string[];
  totals: { ours_cents: number; operator_cents: number; difference_cents: number } | null;
  why: Partial<Record<"ours" | "operator" | "difference", Why>>;
  tiles: Tile[];
  next_decision: NextDecision | null;
}

type State = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Dashboard };

interface Ctx {
  customer: string;
  setCustomer: (c: string) => void;
  site: string;
  setSite: (s: string) => void;
  version: string;
  customers: { id: string; name: string }[];
  load: State;
  retry: () => void;
}

const DashboardContext = createContext<Ctx | null>(null);

export const useDashboard = () => useContext(DashboardContext)!;

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomerState] = useState("");
  const [site, setSiteState] = useState("");
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [load, setLoad] = useState<State>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [version, setVersion] = useState(0);

  const setCustomer = (c: string) => {
    scope.customer_id = c;
    scope.site_id = "";
    setSiteState("");
    setCustomerState(c);
    setVersion((v) => v + 1);
  };

  const setSite = (s: string) => {
    scope.site_id = s;
    setSiteState(s);
    setVersion((v) => v + 1);
  };

  useEffect(() => {
    request<{ id: string; name: string }[]>("/api/demo/customers").then(setCustomers, () => setCustomers([]));
  }, []);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    request<Dashboard>("/api/dashboard")
      .then((data) => {
        if (!live) return;
        if (!scope.customer_id) {
          scope.customer_id = data.customer_id;
          setCustomerState(data.customer_id);
        }
        setLoad({ state: "ready", data });
      })
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [version, attempt]);

  return (
    <DashboardContext.Provider
      value={{
        customer,
        setCustomer,
        site,
        setSite,
        version: String(version),
        customers,
        load,
        retry: () => setAttempt((n) => n + 1),
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function ViewingAs() {
  const { customer, setCustomer, customers } = useDashboard();
  if (!customers.length) return null;
  return (
    <label className="viewing-as">
      <span>Viewing as (demo only):</span>
      <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
        {customers.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </label>
  );
}
