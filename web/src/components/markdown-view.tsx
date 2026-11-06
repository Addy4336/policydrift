import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/** Friendlier titles for the section keys that `policydrift paper` writes. */
const SECTION_TITLES: Record<string, string> = {
  label_distribution: "Label distribution by run",
  h1: "H1 · Outdated answers with the current rule retrieved",
  h1_all_answers: "H1 · All answers (refusals and other labels included)",
  h2: "H2 · Hindi and Gujarati versus English",
  h3_r3: "H3 · Mitigations at R3 (confirmatory)",
  h3_r3_all_answers: "H3 · Mitigations at R3, all answers",
  mitigations_r1_descriptive: "Mitigations at R1 (descriptive)",
  per_fact: "Per fact",
};

function textOf(node: React.ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  return "";
}

const components: Components = {
  h1: () => null, // the page supplies its own title
  h2({ children }) {
    const key = textOf(children).trim();
    const title = SECTION_TITLES[key];
    return (
      <h2>
        {title ?? children}
        {title ? <code className="ml-2 align-middle text-[11px] font-normal text-muted">{key}</code> : null}
      </h2>
    );
  },
  table({ children }) {
    return (
      <div className="table-wrap">
        <table>{children}</table>
      </div>
    );
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    );
  },
};

export function MarkdownView({ source }: { source: string }) {
  return (
    <div className="md text-[15px]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {source}
      </ReactMarkdown>
    </div>
  );
}
