export type EvidenceReference = {
  source_type?: string;
  source_id?: string;
  title?: string;
  source?: string;
  source_section?: string | null;
};

export type ReviewFinding = {
  id: number;
  version_id: number;
  origin: "local" | "ai" | "hybrid";
  check_type?: string | null;
  category: string;
  severity: string;
  excerpt: string;
  explanation: string;
  source_type?: string | null;
  source_id?: string | null;
  source?: string | null;
  source_section?: string | null;
  suggestion?: string | null;
  verification_status: string;
  evidence: EvidenceReference[];
  metadata_json: Record<string, unknown>;
  validation_warnings: string[];
  created_at: string;
};

export type ReviewVersion = {
  id: number;
  review_id: number;
  version_number: number;
  content: string;
  overall_status: "complete" | "partial";
  llm_status: string;
  summary: string;
  retrieval_mode: string;
  retrieved_source_count: number;
  warnings: string[];
  created_at: string;
  findings: ReviewFinding[];
};

export type ReviewDecision = {
  id: number;
  review_id: number;
  version_id: number;
  version_number: number;
  reviewer_name: string;
  decision: "approved" | "needs_revision";
  comment?: string | null;
  acknowledged_partial_review: boolean;
  created_at: string;
};

export type ReviewSummary = {
  id: number;
  title: string;
  status: "submitted" | "needs_revision" | "resubmitted" | "approved";
  current_version_id?: number | null;
  current_version_number?: number | null;
  overall_status?: string | null;
  summary?: string | null;
  finding_count: number;
  created_at: string;
  updated_at: string;
};

export type ReviewDetail = {
  id: number;
  title: string;
  status: "submitted" | "needs_revision" | "resubmitted" | "approved";
  created_at: string;
  updated_at: string;
  current_version?: ReviewVersion | null;
  versions: ReviewVersion[];
  decisions: ReviewDecision[];
};

const API_BASE = (process.env.NEXT_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new Error(`Cannot reach BrandGate API at ${API_BASE}. Check that FastAPI is running.`);
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") message = body.detail;
      else if (body?.detail) message = JSON.stringify(body.detail);
    } catch {
      // Keep the HTTP status message when the response isn't JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function listReviews(): Promise<ReviewSummary[]> {
  return requestJson<ReviewSummary[]>("/api/workflow/reviews");
}

export function getReview(reviewId: number): Promise<ReviewDetail> {
  return requestJson<ReviewDetail>(`/api/workflow/reviews/${reviewId}`);
}

export function createReview(payload: { title: string; content: string; top_k?: number; use_semantic?: boolean }): Promise<ReviewDetail> {
  return requestJson<ReviewDetail>("/api/workflow/reviews", {
    method: "POST",
    body: JSON.stringify({ top_k: 5, use_semantic: true, ...payload }),
  });
}

export function submitRevision(
  reviewId: number,
  payload: { base_version_id: number; content: string; top_k?: number; use_semantic?: boolean },
): Promise<ReviewDetail> {
  return requestJson<ReviewDetail>(`/api/workflow/reviews/${reviewId}/versions`, {
    method: "POST",
    body: JSON.stringify({ top_k: 5, use_semantic: true, ...payload }),
  });
}

export function recordDecision(
  reviewId: number,
  payload: {
    version_id: number;
    reviewer_name: string;
    decision: "approved" | "needs_revision";
    comment?: string;
    acknowledge_partial_review?: boolean;
  },
): Promise<ReviewDetail> {
  return requestJson<ReviewDetail>(`/api/workflow/reviews/${reviewId}/decisions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Apply a suggestion only when it can be matched safely to the current draft. */
export function applySuggestionToContent(
  content: string,
  finding: ReviewFinding,
): { content: string; message: string } | null {
  const replacement = finding.suggestion?.trim();
  if (!replacement) return null;

  const metadata = finding.metadata_json || {};
  const matchedTerm = typeof metadata.matched_term === "string" ? metadata.matched_term : null;
  const positions = Array.isArray(metadata.positions) ? metadata.positions : [];

  if (matchedTerm && positions.length > 0) {
    type Position = { start: number; end: number };
    const sorted = positions.filter((value): value is Position => {
      if (typeof value !== "object" || value === null) return false;
      const candidate = value as Record<string, unknown>;
      return Number.isInteger(candidate.start) && Number.isInteger(candidate.end);
    }).sort((a, b) => b.start - a.start);
    if (sorted.length === 0) return null;
    let updated = content;
    for (const position of sorted) {
      const actual = updated.slice(position.start, position.end);
      if (actual.toLocaleLowerCase() !== matchedTerm.toLocaleLowerCase()) return null;
      updated = updated.slice(0, position.start) + replacement + updated.slice(position.end);
    }
    return { content: updated, message: `Applied terminology suggestion to ${sorted.length} occurrence(s). Review the draft before saving.` };
  }

  const excerpt = finding.excerpt?.trim();
  if (!excerpt) return null;
  const firstIndex = content.indexOf(excerpt);
  if (firstIndex < 0 || content.indexOf(excerpt, firstIndex + excerpt.length) >= 0) return null;
  return {
    content: content.slice(0, firstIndex) + replacement + content.slice(firstIndex + excerpt.length),
    message: "Applied the suggestion to the matching excerpt. Review the draft before saving.",
  };
}
