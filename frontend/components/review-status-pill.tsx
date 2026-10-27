export function ReviewStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    submitted: "bg-blue-50 text-blue-800",
    resubmitted: "bg-indigo-50 text-indigo-800",
    needs_revision: "bg-amber-50 text-amber-800",
    approved: "bg-emerald-50 text-emerald-800",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${colors[status] || "bg-slate-100 text-slate-700"}`}>{status.replaceAll("_", " ")}</span>;
}
