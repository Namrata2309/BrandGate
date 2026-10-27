"use client";

import Link from "next/link";
import { FormEvent, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  applySuggestionToContent,
  getReview,
  recordDecision,
  ReviewDetail,
  ReviewFinding,
  submitRevision,
} from "@/lib/review-workflow-api";
import { ReviewStatusPill } from "@/components/review-status-pill";
import { AppShell } from "@/components/app-shell";

export default function ReviewDetailPage() {
  return (
    <Suspense fallback={<AppShell active="reviews"><main className="mx-auto max-w-7xl px-5 py-12 text-slate-600 sm:px-8">Loading review…</main></AppShell>}>
      <ReviewDetailContent />
    </Suspense>
  );
}

function ReviewDetailContent() {
  const params = useParams<{ id: string }>();
  const reviewId = Number(params.id);
  const [review, setReview] = useState<ReviewDetail | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [reviewerName, setReviewerName] = useState("Brand Reviewer");
  const [comment, setComment] = useState("");
  const [acknowledgePartial, setAcknowledgePartial] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async (discardLocalDraft = false) => {
    if (!Number.isInteger(reviewId) || reviewId <= 0) {
      setError("The review ID in the URL is invalid.");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await getReview(reviewId);
      setReview(data);
      setDraftContent(data.current_version?.content || "");
      setNotice(discardLocalDraft ? "Loaded the latest saved version; unsaved local edits were discarded." : "");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this review.");
    } finally {
      setLoading(false);
    }
  }, [reviewId]);

  useEffect(() => { void refresh(false); }, [refresh]);

  const currentVersion = review?.current_version ?? null;
  const isDirty = Boolean(currentVersion && draftContent !== currentVersion.content);
  const versionsNewestFirst = useMemo(() => review?.versions || [], [review]);

  function onApplySuggestion(finding: ReviewFinding) {
    if (!currentVersion) return;
    const result = applySuggestionToContent(draftContent, finding);
    if (!result) {
      setNotice("This suggestion could not be applied safely to an exact text match. Edit the full draft manually, then save it as a new version.");
      return;
    }
    setDraftContent(result.content);
    setNotice(result.message);
  }

  async function onSaveRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!review || !currentVersion) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await submitRevision(review.id, {
        base_version_id: currentVersion.id,
        content: draftContent,
      });
      setReview(updated);
      setDraftContent(updated.current_version?.content || "");
      setAcknowledgePartial(false);
      setComment("");
      setNotice(`Version ${updated.current_version?.version_number} saved and reviewed. Previous versions and decisions remain in history.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the revision.");
    } finally {
      setBusy(false);
    }
  }

  async function onDecision(decision: "approved" | "needs_revision") {
    if (!review || !currentVersion) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await recordDecision(review.id, {
        version_id: currentVersion.id,
        reviewer_name: reviewerName,
        decision,
        comment,
        acknowledge_partial_review: acknowledgePartial,
      });
      setReview(updated);
      setNotice(decision === "approved"
        ? `Version ${currentVersion.version_number} was approved. The decision is tied to this version only.`
        : `Revision requested for version ${currentVersion.version_number}. Add a new version after editing the draft.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record the decision.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <main className="mx-auto max-w-5xl px-5 py-12 text-slate-600">Loading review…</main>;

  return (
    <AppShell active="reviews">
    <main className="mx-auto max-w-7xl space-y-6 px-5 py-10 text-slate-900 sm:px-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/review" className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-700 hover:text-indigo-900">← All reviews</Link>
          <p className="mt-4 text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">Review #{reviewId}</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">{review?.title || "Content review"}</h1>
          {review && <div className="mt-3 flex flex-wrap items-center gap-2"><ReviewStatusPill status={review.status} />{currentVersion && <span className="text-sm text-slate-500">Version {currentVersion.version_number} · {currentVersion.findings.length} finding(s)</span>}</div>}
        </div>
        <button onClick={() => void refresh(true)} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700">Reload saved version</button>
      </header>

      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
      {notice && <div role="status" className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">{notice}</div>}

      {!review || !currentVersion ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">Review record or content version was not found.</div>
      ) : (
        <>
          <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-5">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><h2 className="text-xl font-semibold">Content findings</h2><p className="mt-1 text-sm text-slate-500">These findings belong to version {currentVersion.version_number}.</p></div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${currentVersion.overall_status === "complete" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>{currentVersion.overall_status === "complete" ? "AI review completed" : `Partial review · ${currentVersion.llm_status}`}</span>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-700">{currentVersion.summary}</p>
                {currentVersion.warnings.length > 0 && <div className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900"><strong>Warnings</strong><ul className="mt-1 list-disc pl-5">{currentVersion.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>}
                {currentVersion.findings.length === 0 ? <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">No findings were returned for this version. This is not a guarantee of perfect compliance; inspect the draft before approving.</p> : (
                  <div className="mt-5 space-y-4">
                    {currentVersion.findings.map((finding) => <FindingCard key={finding.id} finding={finding} onApply={() => onApplySuggestion(finding)} />)}
                  </div>
                )}
              </section>

              <form onSubmit={onSaveRevision} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div><h2 className="text-xl font-semibold">Edit and resubmit</h2><p className="mt-1 text-sm text-slate-500">The original version is immutable. Saving creates a new version and reruns local checks, RAG and contextual review.</p></div>
                <label className="block text-sm font-medium">Editable draft
                  <textarea value={draftContent} onChange={(e) => setDraftContent(e.target.value)} rows={9} maxLength={20000} required className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-3 font-normal leading-6 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
                </label>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className={`text-xs ${isDirty ? "font-semibold text-amber-700" : "text-slate-500"}`}>{isDirty ? "Unsaved changes" : "Draft matches the latest saved version"}</span>
                  <button type="submit" disabled={busy || !isDirty || !draftContent.trim()} className="rounded-xl bg-blue-700 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Saving and reviewing…" : "Save revision and rerun review"}</button>
                </div>
              </form>
            </div>

            <aside className="space-y-5">
              <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div><h2 className="text-xl font-semibold">Reviewer decision</h2><p className="mt-1 text-sm text-slate-500">Decision is recorded against the current version ID ({currentVersion.id}), not just the review ID.</p></div>
                <label className="block text-sm font-medium">Reviewer name
                  <input value={reviewerName} onChange={(e) => setReviewerName(e.target.value)} maxLength={160} required className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
                </label>
                <label className="block text-sm font-medium">Comment
                  <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} maxLength={4000} placeholder="Required when requesting revisions" className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
                </label>
                {currentVersion.overall_status === "partial" && <label className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900"><input type="checkbox" checked={acknowledgePartial} onChange={(e) => setAcknowledgePartial(e.target.checked)} className="mt-1" /><span>I acknowledge that contextual AI review did not fully complete and that I must verify the content independently before approval.</span></label>}
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                  <button type="button" disabled={busy || isDirty || !reviewerName.trim() || (currentVersion.overall_status === "partial" && !acknowledgePartial)} onClick={() => void onDecision("approved")} className="rounded-xl bg-emerald-700 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50">Approve this version</button>
                  <button type="button" disabled={busy || isDirty || !reviewerName.trim() || !comment.trim()} onClick={() => void onDecision("needs_revision")} className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50">Request revision</button>
                </div>
                <p className="text-xs leading-5 text-slate-500">A revision creates a new version. It does not alter previous findings or erase past decisions. Decisions are disabled while this editor has unsaved changes. The API rejects decisions for stale versions.</p>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-semibold">Version history</h2>
                <div className="mt-4 space-y-3">
                  {versionsNewestFirst.map((version) => {
                    const decisionsForVersion = review.decisions.filter((item) => item.version_id === version.id);
                    return <div key={version.id} className={`rounded-xl border p-4 ${version.id === currentVersion.id ? "border-blue-300 bg-blue-50/50" : "border-slate-200"}`}>
                      <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold">Version {version.version_number}</span>{version.id === currentVersion.id && <span className="text-xs font-semibold text-blue-700">Current</span>}</div>
                      <p className="mt-1 text-xs text-slate-500">{new Date(version.created_at).toLocaleString()} · {version.findings.length} finding(s)</p>
                      <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-slate-600">{version.content}</p>
                      {decisionsForVersion.length > 0 && <div className="mt-3 border-t border-slate-200 pt-3">{decisionsForVersion.map((decision) => <p key={decision.id} className="text-xs leading-5 text-slate-600"><strong>{decision.decision.replaceAll("_", " ")}</strong> by {decision.reviewer_name} · version {decision.version_number}{decision.comment ? ` — ${decision.comment}` : ""}</p>)}</div>}
                    </div>;
                  })}
                </div>
              </section>
            </aside>
          </section>
        </>
      )}
    </main>
    </AppShell>
  );
}

function FindingCard({ finding, onApply }: { finding: ReviewFinding; onApply: () => void }) {
  const severityColors: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800",
    medium: "bg-amber-100 text-amber-800",
    warning: "bg-amber-100 text-amber-800",
    low: "bg-blue-100 text-blue-800",
    info: "bg-slate-100 text-slate-700",
  };
  const evidence = finding.evidence || [];
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{finding.category.replaceAll("_", " ")}</span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${severityColors[finding.severity] || severityColors.medium}`}>{finding.severity}</span><span className="text-xs text-slate-500">{finding.origin === "local" ? "Local check" : finding.origin === "hybrid" ? "Local + AI context" : "AI finding"}</span></div>
      <p className="mt-3 text-sm font-semibold text-slate-900">{finding.explanation}</p>
      <div className="mt-3 rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Flagged excerpt</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{finding.excerpt}</p></div>
      {evidence.length > 0 ? <div className="mt-3 space-y-2"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supporting source</p>{evidence.map((source, i) => <div key={`${source.source_id}-${i}`} className="rounded-lg border border-slate-200 p-3 text-sm"><p className="font-semibold">{source.source_id} · {source.title || "Approved source"}</p><p className="mt-1 text-xs text-slate-600">{source.source || "Source not specified"}{source.source_section ? ` · ${source.source_section}` : ""}</p></div>)}</div> : finding.source_id ? <div className="mt-3 rounded-lg border border-slate-200 p-3 text-sm"><p className="font-semibold">{finding.source_id}</p><p className="mt-1 text-xs text-slate-600">{finding.source || "Approved source"}{finding.source_section ? ` · ${finding.source_section}` : ""}</p></div> : <p className="mt-3 text-sm text-amber-800">No verified source is attached. Human verification is required.</p>}
      <p className="mt-3 text-xs text-slate-500">Verification: {finding.verification_status.replaceAll("_", " ")}</p>
      {finding.validation_warnings?.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs text-amber-800">{finding.validation_warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
      {finding.suggestion && <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Suggested correction</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{finding.suggestion}</p><button type="button" onClick={onApply} className="mt-3 rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-semibold text-blue-800 hover:bg-blue-100">Apply to editable draft</button></div>}
    </article>
  );
}
