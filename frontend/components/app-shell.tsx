import Link from "next/link";

type AppShellProps = {
  children: React.ReactNode;
  active?: "overview" | "reviews" | "guidelines";
};

const navigation = [
  { href: "/", label: "Overview", key: "overview" },
  { href: "/review", label: "Review workspace", key: "reviews" },
  { href: "/guidelines", label: "Brand guidelines", key: "guidelines" },
] as const;

export function AppShell({ children, active }: AppShellProps) {
  return (
    <div className="min-h-screen bg-[#f7f8fc] text-slate-950">
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <Link href="/" className="flex items-center gap-3" aria-label="BrandGate overview">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-sm shadow-indigo-200">B</span>
            <span>
              <span className="block text-base font-bold tracking-tight">BrandGate</span>
              <span className="block text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">Content governance</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1 overflow-x-auto" aria-label="Main navigation">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  active === item.key ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="hidden items-center gap-2 text-sm font-semibold text-slate-500 hover:text-indigo-700 lg:flex">
            API docs <span aria-hidden="true">↗</span>
          </a>
        </div>
      </header>
      {children}
      <footer className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-8 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <span>BrandGate · Fictional demo workspace</span>
        <span>Review responsibly. Approval always stays human.</span>
      </footer>
    </div>
  );
}

export function PageIntro({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
      </div>
      {children}
    </div>
  );
}
