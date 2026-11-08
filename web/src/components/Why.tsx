import { useEffect, useId, useRef, useState } from "react";
import type { Why as WhyInfo } from "../api/invoices";

const SURE: Record<WhyInfo["confidence"], string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  "not enough data": "Not enough data",
};

export function Why({ info, label, lead, variant = "full" }: { info: WhyInfo | undefined; label: string; lead?: string; variant?: "full" | "source" }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [pinned, setPinned] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!pos) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent) {
        if (e.key !== "Escape") return;
        button.current?.focus();
      } else if (e.target instanceof Node && (box.current?.contains(e.target) || button.current?.contains(e.target))) {
        return;
      }
      setPos(null);
      setPinned(false);
    };
    document.addEventListener("keydown", close);
    document.addEventListener("mousedown", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("mousedown", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [pos]);

  if (!info) return null;

  const place = () => {
    if (!button.current) return;
    const r = button.current.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 32);
    setPos({ top: r.bottom + 8, left: Math.max(16, Math.min(r.left - 12, window.innerWidth - width - 16)) });
  };
  const toggle = () => {
    if (pinned) {
      setPinned(false);
      setPos(null);
    } else {
      setPinned(true);
      place();
    }
  };

  return (
    <>
      <button
        ref={button}
        type="button"
        className="info-button"
        aria-label={`About this number: ${label}`}
        aria-expanded={pos !== null}
        aria-controls={id}
        onClick={toggle}
        onMouseEnter={() => !pos && place()}
        onMouseLeave={() => !pinned && setPos(null)}
      >
        <span aria-hidden="true">i</span>
      </button>
      {pos && (
        <div ref={box} id={id} role="note" className="why-pop" style={{ top: pos.top, left: pos.left }}>
          {lead && <p className="strong-text">{lead}</p>}
          {variant === "full" && <p>{info.reason ?? info.what}</p>}
          <p>
            <span className="why-key">Where from</span>
            {info.source}
          </p>
          <p>
            <span className="why-key">How sure</span>
            {variant === "source"
              ? `${SURE[info.confidence]}. ${info.reason ?? ""}`.trim()
              : `${SURE[info.confidence]} · ${info.evidence.charAt(0).toUpperCase()}${info.evidence.slice(1)}`}
          </p>
        </div>
      )}
    </>
  );
}
