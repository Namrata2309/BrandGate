import Link from "next/link";
import { AppShell } from "@/components/app-shell";

export default function HomePage() {
  return (
    <AppShell active="overview">
      <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <section className="relative overflow-hidden rounded-3xl bg-slate-950 px-6 py-12 text-white shadow-xl shadow-slate-200 sm:px-12 sm:py-16">
          <div className="absolute -right-20 -top-32 h-80 w-80 rounded-full bg-indigo-500/25 blur-3xl" />
          <div className="relative max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-indigo-100">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Pre-publication control center
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">Make every message unmistakably on-brand.</h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
              BrandGate checks drafts against your approved rules and facts, explains every finding, and keeps final approval in human hands.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/review" className="rounded-xl bg-indigo-500 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-950/30 hover:bg-indigo-400">Start a content review <span aria-hidden="true">→</span></Link>
              <Link href="/guidelines" className="rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white hover:bg-white/15">Manage guidelines</Link>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            { number: "01", title: "Set the standard", text: "Keep brand rules and approved facts in one trusted library." },
            { number: "02", title: "Review with context", text: "Find issues with evidence, source references, and clear suggestions." },
            { number: "03", title: "Approve with confidence", text: "Track revisions and tie every decision to the exact version reviewed." },
          ].map((item) => (
            <section key={item.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/50">
              <span className="text-xs font-bold tracking-[0.18em] text-indigo-600">{item.number}</span>
              <h2 className="mt-4 font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
            </section>
          ))}
        </section>
      </main>
    </AppShell>
  );
}
