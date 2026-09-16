"use client";

import { T } from "@/components/Text";

export default function Error({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section>
      <div className="kicker">ERROR</div>
      <h1 className="display">
        <T zh="后端连不上" en="Backend unavailable" />
      </h1>
      <p className="date-line">{error.message}</p>
      <button className="back press" type="button" onClick={reset}>
        <T zh="重试" en="Retry" />
      </button>
    </section>
  );
}