import type { Text as TextPair } from "@/data/types";

type Props = TextPair & {
  as?: "span" | "fragment";
};

export function T({ zh, en, as = "span" }: Props) {
  if (as === "fragment") {
    return (
      <>
        <span className="t-zh">{zh}</span>
        <span className="t-en">{en}</span>
      </>
    );
  }
  return (
    <>
      <span className="t-zh">{zh}</span>
      <span className="t-en">{en}</span>
    </>
  );
}

export function tx(pair: TextPair) {
  return <T zh={pair.zh} en={pair.en} />;
}