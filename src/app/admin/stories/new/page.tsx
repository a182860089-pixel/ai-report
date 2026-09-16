"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { T } from "@/components/Text";
import { Banner, asErrorMessage } from "@/components/admin/ui";
import { StoryForm, blankStory, storyPayload } from "@/components/admin/StoryForm";
import { adminApi } from "@/lib/admin-api";

function NewStoryInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [draft, setDraft] = useState(() => blankStory(params.get("date") ?? ""));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <section>
      <div className="desk-kicker">NEW CLUSTER</div>
      <h1 className="desk-title">
        <T zh="新开一簇" en="New cluster" />
      </h1>
      <p className="desk-lead">
        <T zh="目标日必须已经有早报（草稿也行）。" en="The target date must already have a briefing, draft included." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <StoryForm
        creating
        draft={draft}
        onChange={setDraft}
        busy={busy}
        onSubmit={async () => {
          setBusy(true);
          setError(null);
          try {
            const created = await adminApi.createStory(storyPayload(draft, true));
            router.replace(`/admin/stories/${created.slug}`);
          } catch (err) {
            setError(asErrorMessage(err));
          } finally {
            setBusy(false);
          }
        }}
      />
    </section>
  );
}

export default function NewStoryPage() {
  return (
    <Suspense fallback={<p className="desk-hint">…</p>}>
      <NewStoryInner />
    </Suspense>
  );
}