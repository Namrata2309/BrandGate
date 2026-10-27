'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { AppShell, PageIntro } from '@/components/app-shell';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

type BrandRule = {
  id: number;
  rule_code: string;
  category: string;
  title: string;
  rule_text: string;
  source: string;
  source_section: string | null;
  severity: string;
  status: string;
  effective_date: string | null;
};

const emptyForm = {
  rule_code: '',
  category: 'tone',
  title: '',
  rule_text: '',
  source: 'Northstar Brand Guide',
  source_section: '',
  severity: 'warning',
};

export default function GuidelinesPage() {
  const [rules, setRules] = useState<BrandRule[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/api/rules?status=all`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load rules (HTTP ${response.status}).`);
      setRules(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect to the BrandGate API.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');

    try {
      const response = await fetch(`${API_BASE}/api/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          source_section: form.source_section.trim() || null,
          status: 'active',
        }),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : `Could not save rule (HTTP ${response.status}).`;
        throw new Error(detail);
      }

      setNotice(`Rule ${body.rule_code} created successfully.`);
      setForm(emptyForm);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the rule.');
    } finally {
      setSaving(false);
    }
  }

  async function deactivateRule(rule: BrandRule) {
    if (!window.confirm(`Deactivate ${rule.rule_code}? Existing review history will be preserved.`)) return;
    setError('');
    setNotice('');
    try {
      const response = await fetch(`${API_BASE}/api/rules/${rule.id}`, { method: 'DELETE' });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `Could not deactivate rule (HTTP ${response.status}).`);
      setNotice(`${rule.rule_code} deactivated.`);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not deactivate the rule.');
    }
  }

  return (
    <AppShell active="guidelines">
      <main className="mx-auto max-w-7xl space-y-8 px-5 py-10 text-slate-900 sm:px-8">
        <PageIntro eyebrow="Brand foundation" title="Brand guidelines" description="Manage the approved rules that BrandGate uses when checking content. Every rule keeps its source so findings remain explainable.">
          <Link href="/review" className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold shadow-sm hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700">Go to review workspace</Link>
        </PageIntro>

        {error && <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
        {notice && <div role="status" className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</div>}

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.82fr)]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/50 sm:p-7">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Rule library</h2>
                <p className="mt-1 text-sm text-slate-500">{rules.length} rule(s), including inactive rules</p>
              </div>
              <button onClick={() => void loadRules()} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50">Refresh</button>
            </div>

            {loading ? (
              <p className="py-10 text-center text-sm text-slate-500">Loading rules…</p>
            ) : rules.length === 0 ? (
              <p className="rounded-xl bg-slate-50 p-5 text-sm text-slate-600">No rules yet. Add one using the form.</p>
            ) : (
              <div className="space-y-3">
                {rules.map((rule) => (
                  <article key={rule.id} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-md bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700">{rule.rule_code}</span>
                      <span className="text-xs text-slate-500">{rule.category.replaceAll('_', ' ')}</span>
                      <span className={`ml-auto rounded-full px-2 py-1 text-xs font-semibold ${rule.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{rule.status}</span>
                    </div>
                    <h3 className="mt-3 font-semibold">{rule.title}</h3>
                    <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">{rule.rule_text}</p>
                    <p className="mt-3 text-xs text-slate-500">Source: {rule.source}{rule.source_section ? ` · ${rule.source_section}` : ''}</p>
                    {rule.status === 'active' && (
                      <button onClick={() => void deactivateRule(rule)} className="mt-3 text-xs font-semibold text-red-700 hover:text-red-900">Deactivate rule</button>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="h-fit rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/50 sm:p-7">
            <h2 className="text-lg font-semibold">Add a brand rule</h2>
            <p className="mb-5 mt-1 text-sm leading-6 text-slate-500">Give each rule a stable ID and a source so future findings can explain which guideline they used.</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium">Rule code
                  <input required minLength={3} maxLength={40} value={form.rule_code} onChange={(e) => setForm({ ...form, rule_code: e.target.value.trim().toUpperCase() })} placeholder="BG-007" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
                </label>
                <label className="block text-sm font-medium">Category
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500">
                    <option value="tone">Tone</option><option value="terminology">Terminology</option><option value="promotional_claim">Promotional claim</option><option value="messaging">Messaging</option><option value="facts">Facts</option><option value="accessibility">Accessibility</option><option value="visual_identity">Visual identity</option>
                  </select>
                </label>
              </div>
              <label className="block text-sm font-medium">Title
                <input required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Use approved product terminology" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
              </label>
              <label className="block text-sm font-medium">Rule text
                <textarea required minLength={5} rows={4} value={form.rule_text} onChange={(e) => setForm({ ...form, rule_text: e.target.value })} placeholder="Describe what content creators should or should not do…" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium">Source
                  <input required value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
                </label>
                <label className="block text-sm font-medium">Source section (optional)
                  <input value={form.source_section} onChange={(e) => setForm({ ...form, source_section: e.target.value })} placeholder="Section 2" className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
                </label>
              </div>
              <label className="block text-sm font-medium">Severity
                <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500">
                  <option value="info">Info</option><option value="warning">Warning</option><option value="high">High</option><option value="critical">Critical</option>
                </select>
              </label>
              <button disabled={saving} type="submit" className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
                {saving ? 'Saving rule…' : 'Add rule'}
              </button>
            </form>
          </section>
        </div>
      </main>
    </AppShell>
  );
}
