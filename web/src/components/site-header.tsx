"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DEMO_FIXTURES } from "@/lib/api";
import { LogoMark } from "./icons";
import { useLanguage } from "./language-provider";

export function SiteHeader() {
  const pathname = usePathname();
  const { t } = useLanguage();
  const links = [
    { href: "/", label: t.navAsk },
    { href: "/schemes", label: t.navSchemes },
    { href: "/research", label: t.navResearch },
  ] as const;

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/90 backdrop-blur supports-[backdrop-filter]:bg-bg/75">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 rounded-md">
          <LogoMark className="h-7 w-7 shrink-0" />
          <span className="text-[15px] font-semibold tracking-tight">PolicyDrift</span>
        </Link>
        <nav aria-label="Main">
          <ul className="flex items-center gap-0.5 sm:gap-1">
            {links.map((l) => {
              const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
              return (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-md px-2.5 py-1.5 text-sm transition-colors sm:px-3 ${
                      active
                        ? "bg-accent-soft font-medium text-accent-strong"
                        : "text-muted hover:bg-surface-2 hover:text-text"
                    }`}
                  >
                    {l.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
      {DEMO_FIXTURES ? (
        <div className="border-t border-warn-border bg-warn-soft px-4 py-1 text-center text-xs text-warn">
          {t.demoMode}
        </div>
      ) : null}
    </header>
  );
}
