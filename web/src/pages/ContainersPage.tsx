import { useEffect, useState } from "react";
import { getContainers, postContainerDecision, type ContainerCard, type Containers } from "../api/containers";
import { FootNote, InfoIcon, PageTitle } from "../components/ui";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Containers };

const DONE: Record<string, string> = { approve: "Approved. Applied only in your plan, nothing sent.", prepare: "Check requested. Nothing sent.", not_now: "Not now." };
const t1 = (kg: number) => `${(kg / 1000).toFixed(1)}`;

export function ContainersPage() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getContainers()
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt]);

  const decide = async (c: ContainerCard, decision: "approve" | "not_now" | "prepare") => {
    setBusy(c.id);
    try {
      await postContainerDecision(c.id, decision);
      setAttempt((a) => a + 1);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageTitle
        title="Containers"
        subtitle="Suggested changes to pickup rules. Smart Weight applies them only after you approve."
        context=""
      />
      {load.state === "loading" && <p className="status-text" role="status">Loading</p>}
      {load.state === "failed" && (
        <div className="status-text" role="alert">
          <p>Could not load. Try again.</p>
          <button type="button" className="btn btn-outline" onClick={() => setAttempt((a) => a + 1)}>
            Try again
          </button>
        </div>
      )}
      {load.state === "ready" &&
        (load.data.cards.length === 0 ? (
          <p className="status-text">No changes to suggest right now.</p>
        ) : (
          <div className="ct-list">
            {load.data.cards.map((c) => (
              <section key={c.id} className={c.highlight ? "card ct-card is-check" : "card ct-card"} aria-label={`${c.material}, ${c.site}`}>
                <div className="ct-name">
                  <h2>{c.material}</h2>
                  <p>{c.site}</p>
                  {c.highlight && c.fill && (
                    <span className="ct-fill">
                      <span className="ct-track">
                        <span className="ct-bar" style={{ width: `${Math.min(100, (c.fill.now_kg / c.fill.target_kg) * 100)}%` }} />
                        <span className="ct-marker" aria-hidden="true" />
                      </span>
                      <span className="ct-fill-text">
                        {t1(c.fill.now_kg)} / {t1(c.fill.target_kg)} t<br />
                        now
                      </span>
                    </span>
                  )}
                </div>
                {c.kind === "rule" ? (
                  <p className="ct-rule">
                    <s>{c.old_rule}</s>
                    <span className="ct-arrow" aria-hidden="true">
                      →
                    </span>
                    <span className="ct-pill">{c.new_rule}</span>
                  </p>
                ) : (
                  <p className="ct-rule">
                    <span className="ct-pill is-check">{c.new_rule}</span>
                  </p>
                )}
                <div className="ct-estimate">
                  {c.kind === "rule" ? (
                    <>
                      <span className="ct-big">
                        {c.estimate}
                        {c.why && <InfoIcon info={c.why} label={`estimate for ${c.material}`} />}
                      </span>
                      <span className="sub-small">{c.estimate_note}</span>
                    </>
                  ) : (
                    <>
                      <span className="ct-sensor">{c.sensor?.text}</span>
                      <span className="sub-small">{c.sensor?.since}</span>
                    </>
                  )}
                </div>
                <div className="ct-actions">
                  {c.decision ? (
                    <span className="sub-small">{DONE[c.decision] ?? "Saved."}</span>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn btn-primary"
                        disabled={busy === c.id}
                        onClick={() => decide(c, c.kind === "rule" ? "approve" : "prepare")}
                      >
                        {c.kind === "rule" ? "Approve" : "Book a check"}
                      </button>
                      <button type="button" className="btn btn-outline" disabled={busy === c.id} onClick={() => decide(c, "not_now")}>
                        Not now
                      </button>
                    </>
                  )}
                </div>
              </section>
            ))}
          </div>
        ))}
      <FootNote>Every rule keeps the maximum days between pickups and your site closures. Savings are estimates. Demo data.</FootNote>
    </>
  );
}
