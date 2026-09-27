import { useMemo, useState } from "react";
import { isSummaryHeading, parseInline, parseSections } from "../lib/markdown";

interface Props {
  content: string;
  /** Sections start open; the first is always open. */
  defaultOpen?: number;
}

/** Render one line, turning `**figure**` into emphasis. */
function InlineText({ text }: { text: string }) {
  const runs = useMemo(() => parseInline(text), [text]);
  return (
    <>
      {runs.map((r, i) =>
        r.bold ? (
          <strong key={i} className="doc-strong">
            {r.text}
          </strong>
        ) : (
          <span key={i}>{r.text}</span>
        ),
      )}
    </>
  );
}

/**
 * The generated report, folded into `## ` sections. Content is the provider's
 * own text, verbatim — this component only groups and hides it.
 */
export default function ReportDoc({ content, defaultOpen = 1 }: Props) {
  const { title, sections } = useMemo(() => parseSections(content), [content]);
  const [open, setOpen] = useState<Set<number>>(
    () => new Set(sections.slice(0, defaultOpen).map((_, i) => i)),
  );

  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="doc">
      {title && <h2 className="doc-h1">{title}</h2>}
      {sections.map((section, i) => {
        const isOpen = open.has(i);
        const summary = isSummaryHeading(section.heading);
        return (
          <section key={`${section.heading}-${i}`}>
            <button
              className="doc-fold"
              onClick={() => toggle(i)}
              aria-expanded={isOpen}
              aria-controls={`sec-${i}`}
            >
              <span className="n">{String(i + 1).padStart(2, "0")}</span>
              <span>{section.heading}</span>
              <span className="caret" aria-hidden="true">
                {isOpen ? "−" : "+"}
              </span>
            </button>
            {isOpen && (
              <div
                className={`doc-fold-body${summary ? " doc-summary" : ""}`}
                id={`sec-${i}`}
              >
                {section.blocks.map((b, j) => {
                  if (b.kind === "gap") return null;
                  if (b.kind === "h3") return <h4 key={j} className="doc-h3">{b.text}</h4>;
                  if (b.kind === "li")
                    return (
                      <div key={j} className="doc-li">
                        — <InlineText text={b.text} />
                      </div>
                    );
                  return (
                    <p key={j} className="doc-p">
                      <InlineText text={b.text} />
                    </p>
                  );
                })}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
