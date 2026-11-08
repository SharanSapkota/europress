import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router";
import type { Why as WhyInfo } from "../api/invoices";
import { useDashboard } from "./HeaderTools";
import { Why } from "./Why";

export function InfoIcon({ info, label, lead, variant }: { info: WhyInfo | undefined; label: string; lead?: string; variant?: "full" | "source" }) {
  return <Why info={info} label={label} lead={lead} variant={variant} />;
}

export function PageTitle({ title, subtitle, context, right }: { title: string; subtitle?: string; context?: string; right?: ReactNode }) {
  const { load } = useDashboard();
  const fallback =
    load.state === "ready" && load.data.customer_name
      ? `${load.data.customer_name} · ${load.data.sites.length} ${load.data.sites.length === 1 ? "site" : "sites"}`
      : undefined;
  const line = context ?? fallback;
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
        {line && <p className="page-context">{line}</p>}
      </div>
      {right}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`.trim()}>{children}</section>;
}

export interface TotalsItem {
  label: string;
  value: string;
  info?: WhyInfo;
  tag?: string;
}

export function TotalsPanel({ items }: { items: TotalsItem[] }) {
  return (
    <dl className="totals-panel">
      {items.map((x, i) => (
        <div key={x.label} className={i === 2 ? "totals-cell is-key" : "totals-cell"}>
          <dt>{x.label}</dt>
          <dd>
            {x.value}
            {x.info && <InfoIcon info={x.info} label={x.label} />}
          </dd>
          {x.tag && <dd className="totals-tag">{x.tag}</dd>}
        </div>
      ))}
    </dl>
  );
}

export function StatTile({ label, value, check = false, to }: { label: string; value: string; check?: boolean; to?: string }) {
  const body = (
    <>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </>
  );
  const cls = check ? "stat-tile is-check" : "stat-tile";
  return to ? (
    <Link to={to} className={cls}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="stat-row">{children}</div>;
}

export function InfoLine({ children }: { children: ReactNode }) {
  return (
    <p className="info-line">
      <span className="info-button" aria-hidden="true">
        i
      </span>
      {children}
    </p>
  );
}

export function DataTable({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`table-card ${className}`.trim()}>
      <div className="table-box">{children}</div>
    </div>
  );
}

export function TableHeader({ cells }: { cells: ReactNode[] }) {
  return (
    <thead className="table-head">
      <tr>
        {cells.map((c, i) => (
          <th key={i} scope="col">
            {c}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export type ChipTone = "check" | "good" | "neutral" | "blue" | "disputed";

export function Chip({ tone, children }: { tone: ChipTone; children: ReactNode }) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}

export function Button({ variant = "outline", ...rest }: { variant?: "primary" | "outline" } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" {...rest} className={`btn btn-${variant}`} />;
}

export function FootNote({ children }: { children: ReactNode }) {
  return <p className="foot-note">{children}</p>;
}
