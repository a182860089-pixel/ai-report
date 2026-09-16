"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, ConfirmButton, asErrorMessage } from "@/components/admin/ui";
import { StoryForm, fromAdminStory, storyPayload, type StoryDraft } from "@/components/admin/StoryForm";
import { adminApi } from "@/lib/admin-api";

export default function EditStoryPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;
  const [draft, setDraft] = useState<StoryDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    adminApi
      .story(slug)
      .then((story) => setDraft(fromAdminStory(story)))
      .catch((err) => setError(asErrorMessage(err)));
  }, [slug]);

  return (
    <section>
      <div className="desk-kicker">CLUSTER</div>
      <h1 className="desk-title">{slug}</h1>
      {draft ? (
        <p className="desk-lead">
          <Link href={`/admin/briefings/${draft.date}`}>{draft.date}</Link>
          {" · "}
          <Link href={`/story/${slug}`}>
            <T zh="公开页" en="Public page" />
          </Link>
        </p>
      ) : null}
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}
      {draft ? (
        <>
          <div className="desk-toolbar">
            <ConfirmButton
              className="desk-btn ghost danger"
              label={<T zh="删簇" en="Delete story" />}
              confirm={<T zh="确认删簇？" en="Delete cluster?" />}
              onConfirm={async () => {
                setError(null);
                try {
                  await adminApi.deleteStory(slug);
                  router.replace(`/admin/briefings/${draft.date}`);
                } catch (err) {
                  setError(asErrorMessage(err));
                }
              }}
            />
          </div>
          <StoryForm
            creating={false}
            draft={draft}
            busy={busy}
            onChange={setDraft}
            onSubmit={async () => {
              setBusy(true);
              setError(null);
              setOk(null);
              try {
                const saved = await adminApi.patchStory(slug, storyPayload(draft, false));
                setDraft(fromAdminStory(saved));
                setOk("Story saved.");
              } catch (err) {
                setError(asErrorMessage(err));
              } finally {
                setBusy(false);
              }
            }}
          />
        </>
      ) : null}
    </section>
  );
}