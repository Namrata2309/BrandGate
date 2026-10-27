"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createReview, listReviews, ReviewSummary } from "@/lib/review-workflow-api";
import { ReviewStatusPill } from "@/components/review-status-pill";
import { AppShell, PageIntro } from "@/components/app-shell";

const DEMO_DRAFT = "Our Dashboard guarantees every business will double its sales. Get access for only ₹799 per month!";

export default function ReviewWorkspacePage() {
  const router = useRouter();
  const [title, setTitle] = useState("Northstar Workspace social post");
  const [content, setContent] = useState(DEMO_DRAFT);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const refreshReviews = useCallback(async () => {
    setLoadingList(true);
    try {
      setReviews(await listReviews());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load reviews.");
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => { void refreshReviews(); }, [refreshReviews]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const result = await createReview({ title, content });
      router.push(`/review/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create review.");
      setSubmitting(false);
    }
  }

  return (
    <AppShell active="reviews">
      <main className="mx-auto max-w-7xl space-y-8 px-5 py-10 text-slate-900 sm:px-8">
      <PageIntro eyebrow="Content governance" title="Review workspace" description="Submit a draft, inspect evidence-backed findings, apply suggestions, and record a human decision for a specific version.">
        <Link href="/guidelines" className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700">Manage guidelines</Link>
      </PageIntro>

      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/50 sm:p-7">
          <div>
            <div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-sm font-bold text-indigo-700">1</span><h2 className="text-xl font-semibold">Start a content review</h2></div>
            <p className="mt-1 text-sm text-slate-500">The first review creates version 1 and saves its findings.</p>
          </div>
          <label className="block text-sm font-medium">Review title
            <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} required className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
          </label>
          <label className="block text-sm font-medium">Draft content
            <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={8} maxLength={20000} required className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-3 font-normal leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
          </label>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button type="button" onClick={() => setContent(DEMO_DRAFT)} className="text-sm font-semibold text-slate-600 hover:text-slate-900">Load demo draft</button>
            <button disabled={submitting || !content.trim() || !title.trim()} className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-indigo-200 hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
              {submitting ? "Reviewing content…" : "Run review and save"}
            </button>
          </div>
          <p className="text-xs leading-5 text-slate-500">The review may take a little longer when the hosted AI provider is responding. If AI analysis fails, the system should preserve local findings and clearly mark the review as partial.</p>
        </form>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/50 sm:p-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-sm font-bold text-slate-600">2</span><h2 className="text-xl font-semibold">Recent reviews</h2></div>
              <p className="mt-1 text-sm text-slate-500">Saved records and their latest versions.</p>
            </div>
            <button onClick={() => void refreshReviews()} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50">Refresh</button>
          </div>
          {loadingList ? <p className="mt-6 text-sm text-slate-500">Loading reviews…</p> : reviews.length === 0 ? (
            <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">No saved reviews yet. Submit your first draft to start.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {reviews.map((review) => (
                <Link key={review.id} href={`/review/${review.id}`} className="block rounded-xl border border-slate-200 p-4 transition hover:border-blue-300 hover:bg-blue-50/40">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <span className="font-semibold">{review.title}</span>
                    <ReviewStatusPill status={review.status} />
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Review #{review.id} · Version {review.current_version_number ?? "—"} · {review.finding_count} finding(s)</p>
                  <p className="mt-2 line-clamp-2 text-sm text-slate-600">{review.summary || "No summary available."}</p>
                </Link>
              ))}
            </div>
          )}
        </section>
      </section>
      </main>
    </AppShell>
  );
}
