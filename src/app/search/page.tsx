import { Suspense } from "react";
import { T } from "@/components/Text";
import { SearchPanel } from "./SearchPanel";

export const metadata = { title: "搜索" };

export default function SearchPage() {
  return (
    <section>
      <div className="kicker">SEARCH</div>
      <h1 className="display">
        <T zh="搜事件，不搜标题" en="Search events, not headlines" />
      </h1>
      <Suspense>
        <SearchPanel />
      </Suspense>
    </section>
  );
}