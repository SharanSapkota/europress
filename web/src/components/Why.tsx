import { useEffect, useId, useRef, useState } from "react";
import type { Why as WhyInfo } from "../api/invoices";

const SURE: Record<WhyInfo["confidence"], string> = {
  high: "High",
  low: "Low",
  "not enough data": "Not enough data",
};

export function Why({ info, label }: { info: WhyInfo | undefined; label: string }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
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

  const toggle = () => {
    if (pos || !button.current) return setPos(null);
    const r = button.current.getBoundingClientRect();
    const width = Math.min(320, window.innerWidth - 32);
    setPos({ top: r.bottom + 6, left: Math.max(16, Math.min(r.left, window.innerWidth - width - 16)) });
  };

  return (
    <>
      <button
        ref={button}
        type="button"
        className="why-button"
        aria-expanded={pos !== null}
        aria-controls={id}
        onClick={toggle}
      >
        Why?<span className="visually-hidden"> {label}</span>
      </button>
      {pos && (
        <div ref={box} id={id} role="note" className="why-pop" style={{ top: pos.top, left: pos.left }}>
          <p>{info.reason ?? info.what}</p>
          <p>
            <span className="why-key">From:</span> {info.source}
          </p>
          <p>
            <span className="why-key">How sure:</span> {SURE[info.confidence]} · {info.evidence.charAt(0).toUpperCase()}
            {info.evidence.slice(1)}
          </p>
        </div>
      )}
    </>
  );
}
