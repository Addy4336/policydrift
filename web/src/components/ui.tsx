import type { ReactNode } from "react";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "border-border bg-surface-2 text-muted",
  accent: "border-transparent bg-accent-soft text-accent-strong",
  ok: "border-transparent bg-ok-soft text-ok",
  warn: "border-warn-border bg-warn-soft text-warn",
  danger: "border-transparent bg-danger-soft text-danger",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium leading-5 ${TONES[tone]} ${className ?? ""}`}
    >
      {children}
    </span>
  );
}

export function Card({
  children,
  className,
  as: Tag = "section",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "aside";
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag className={`rounded-xl border border-border bg-surface ${className ?? ""}`} {...rest}>
      {children}
    </Tag>
  );
}

export function CardHeading({ children, id, aside }: { children: ReactNode; id?: string; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
      <h2 id={id} className="text-xs font-semibold uppercase tracking-wider text-muted">
        {children}
      </h2>
      {aside}
    </div>
  );
}

export function ErrorNotice({ title, message }: { title: string; message: string }) {
  return (
    <div role="alert" className="rounded-xl border border-danger/40 bg-danger-soft px-4 py-3 text-sm">
      <p className="font-medium text-danger">{title}</p>
      <p className="mt-0.5 text-text">{message}</p>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-2 ${className ?? ""}`} aria-hidden />;
}
