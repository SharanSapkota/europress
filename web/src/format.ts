const money = new Intl.NumberFormat("fi-FI", { style: "currency", currency: "EUR" });
const tonnes = new Intl.NumberFormat("fi-FI", { maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("fi-FI", { maximumFractionDigits: 3 });

export const eur = (cents: number) => money.format(cents / 100);

export const signedEur = (cents: number) => (cents > 0 ? "+" : cents < 0 ? "−" : "") + money.format(Math.abs(cents) / 100);

export const t = (kg: number) => `${tonnes.format(kg / 1000)} t`;

export const qty = (n: number | null) => (n === null ? "" : num.format(n));

export const day = (iso: string | null) =>
  iso ? new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "–";

export const month = (period: string) =>
  new Date(`${period}-15T12:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

export const material = (m: string | null) => (m ? m.charAt(0).toUpperCase() + m.slice(1).replace(/_/g, " ") : "–");
