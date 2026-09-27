/** Markdown section parser for the generated report.
 *
 * Split out of the component so it can be unit tested without a DOM: the
 * folding behaviour depends entirely on this grouping, and a silent
 * mis-parse would show a report with the wrong sections.
 *
 * The parser never rewrites wording. It only groups the provider's own lines.
 */

export interface Block {
  kind: "h1" | "h2" | "h3" | "li" | "p" | "gap";
  text: string;
}

export interface Section {
  heading: string;
  blocks: Block[];
}

export interface ParsedReport {
  title: string | null;
  sections: Section[];
}

export function parseSections(content: string): ParsedReport {
  const lines = content.split("\n");
  let title: string | null = null;
  const sections: Section[] = [];
  let current: Section | null = null;
  const preamble: Block[] = [];

  const push = (b: Block) => {
    if (current) current.blocks.push(b);
    else preamble.push(b);
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("# ")) {
      title = line.slice(2).trim();
      continue;
    }
    if (line.startsWith("## ")) {
      current = { heading: line.slice(3).trim(), blocks: [] };
      sections.push(current);
      continue;
    }
    if (line.startsWith("### ")) {
      push({ kind: "h3", text: line.slice(4).trim() });
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      push({ kind: "li", text: line.slice(2).trim() });
      continue;
    }
    if (line === "") {
      push({ kind: "gap", text: "" });
      continue;
    }
    push({ kind: "p", text: raw });
  }

  // Anything before the first `##` heading belongs to the document summary.
  if (preamble.some((b) => b.kind !== "gap")) {
    sections.unshift({ heading: "Summary", blocks: preamble });
  }
  return { title, sections };
}

/** True when a section reads as the executive summary. */
export function isSummaryHeading(heading: string): boolean {
  return /executive summary|summary/i.test(heading);
}

/** One inline run of a paragraph: either emphasised or plain. */
export interface Inline {
  text: string;
  bold: boolean;
}

/**
 * Split a line into inline runs on `**bold**`.
 *
 * The provider wraps its key figures in double asterisks; rendering the line
 * verbatim would show literal `**` around every number, so emphasis is parsed
 * out here. Only the markers are interpreted — the words themselves are never
 * altered.
 */
export function parseInline(line: string): Inline[] {
  const runs: Inline[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) runs.push({ text: line.slice(last, m.index), bold: false });
    runs.push({ text: m[1], bold: true });
    last = m.index + m[0].length;
  }
  if (last < line.length) runs.push({ text: line.slice(last), bold: false });
  return runs.length > 0 ? runs : [{ text: line, bold: false }];
}
