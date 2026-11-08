import { useEffect, useState } from "react";
import { request } from "../api/invoices";
import { FeatureCard, type Card } from "../components/FeatureCard";
import { FootNote, PageTitle } from "../components/ui";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; cards: Card[] };

export function FeaturePage({ title, endpoint }: { title: string; endpoint: string }) {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    request<{ cards: Card[] }>(endpoint)
      .then((d) => live && setLoad({ state: "ready", cards: d.cards }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [endpoint, attempt]);

  return (
    <>
      <PageTitle title={title} subtitle="All months in the data." />
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
        (load.cards.length === 0 ? (
          <p className="status-text">Nothing to show yet.</p>
        ) : (
          <>
            <div className="fcards">
              {[...load.cards]
                .sort((a, b) => a.rank - b.rank)
                .slice(0, all ? undefined : 3)
                .map((c) => (
                  <FeatureCard key={c.id} card={c} endpoint={endpoint} />
                ))}
            </div>
            {load.cards.length > 3 && !all && (
              <button type="button" className="link" onClick={() => setAll(true)}>
                Show all ({load.cards.length})
              </button>
            )}
          </>
        ))}
      <FootNote>Suggestions only. Nothing is sent without your approval. Savings are estimates. Demo data.</FootNote>
    </>
  );
}
