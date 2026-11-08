import { NavLink } from "react-router";

const TABS: [string, string][] = [
  ["/", "Dashboard"],
  ["/invoices", "Invoices"],
  ["/costs", "Cost per tonne"],
  ["/operators", "Operators"],
  ["/containers", "Containers"],
  ["/value", "Value"],
  ["/decisions", "Decisions"],
];

export function Header() {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/" className="brand-link" aria-label="Smart Weight, dashboard">
          <span className="logo-tile" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path
                d="M12 3v18M7 21h10M5 7h14M5 7l-3 6a3 3 0 0 0 6 0L5 7Zm14 0-3 6a3 3 0 0 0 6 0l-3-6Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="brand">Smart Weight</span>
        </NavLink>
        <nav aria-label="Main" className="nav">
          {TABS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className="nav-link">
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
