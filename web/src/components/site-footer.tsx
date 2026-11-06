"use client";

import Link from "next/link";
import { useLanguage } from "./language-provider";

export function SiteFooter() {
  const { t } = useLanguage();
  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-sm text-muted sm:grid-cols-[1fr_auto] sm:px-6">
        <div className="space-y-1.5">
          <p>{t.footerSources}</p>
          <p>{t.footerLegal}</p>
          <p className="text-xs">
            PolicyDrift is an independent research project and is not affiliated with the Government of India.
          </p>
        </div>
        <div className="text-xs sm:text-right">
          <p className="font-medium text-text">Stale by Default</p>
          <p>Measuring and mitigating outdated-rule answers</p>
          <p>in multilingual policy RAG agents</p>
          <Link href="/research" className="mt-1 inline-block text-accent underline-offset-2 hover:underline">
            {t.navResearch} →
          </Link>
        </div>
      </div>
    </footer>
  );
}
