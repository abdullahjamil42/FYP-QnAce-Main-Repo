import { getSupabaseClient } from "./supabase";

const BUCKET = "Notes";

/** Strip file extension only → use as display label (keeps "2. programming" etc.). */
function toLabel(name: string): string {
  return name.replace(/\.[^/.]+$/, "").trim();
}

/**
 * Returns the list of note files that actually exist in the bucket.
 * Tries the SDK list API first (requires SELECT policy on storage.objects).
 * Falls back to probing public URLs for all known filename patterns.
 */
export async function listNoteTopics(): Promise<{ file: string; label: string }[]> {
  const supabase = getSupabaseClient();
  if (!supabase) return [];

  // Primary: SDK list (works if Supabase storage SELECT policy is set)
  const { data } = await supabase.storage.from(BUCKET).list("", { limit: 200 });
  // Filter FIRST — Supabase auto-inserts a `.emptyFolderPlaceholder` sentinel file,
  // which would make data.length > 0 true while yielding zero real files.
  const realFiles = (data ?? []).filter((f) => /\.(md|txt)$/i.test(f.name));
  return realFiles
    .map((f) => ({ file: f.name, label: toLabel(f.name) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

// ---------------------------------------------------------------------------
// Plain-text → Markdown preprocessor
// ---------------------------------------------------------------------------

/** Map of bare language labels used in the notes file → fenced-code-block language ids */
const CODE_LANG_MAP: Record<string, string> = {
  JavaScript: "javascript",
  TypeScript: "typescript",
  Python:     "python",
  Java:       "java",
  C:          "c",
  "C++":      "cpp",
  Go:         "go",
  YAML:       "yaml",
  Bash:       "bash",
  JSON:       "json",
  Rust:       "rust",
  HTML:       "html",
  CSS:        "css",
  SQL:        "sql",
};

function findNextNonBlank(lines: string[], start: number): number | null {
  for (let j = start; j < lines.length; j++) {
    if (lines[j].trim()) return j;
  }
  return null;
}

/** Returns true if a line looks like source code rather than prose. */
function isCodeishLine(line: string): boolean {
  const s = line.trimStart();
  if (!s) return false;
  if (/^(\s{4}|\t)/.test(line)) return true; // 4-space or tab indent
  return (
    s.startsWith("// ") || s === "//" ||
    s.startsWith("# ") || s === "#" ||
    s.startsWith("/* ") || s.startsWith(" * ") || s.endsWith("*/") ||
    s.startsWith("import ") || s.startsWith("export ") || s.startsWith("from ") ||
    s.startsWith("function ") || s.startsWith("async function") ||
    s.startsWith("const ") || s.startsWith("let ") || s.startsWith("var ") ||
    s.startsWith("class ") || s.startsWith("interface ") ||
    s.startsWith("def ") || s.startsWith("async def ") ||
    s.startsWith("public ") || s.startsWith("private ") || s.startsWith("protected ") ||
    s.startsWith("static ") || s.startsWith("abstract ") || s.startsWith("@Override") ||
    s.startsWith("int ") || s.startsWith("void ") || s.startsWith("bool ") || s.startsWith("double ") || s.startsWith("String ") ||
    s.startsWith("return ") || s.startsWith("throw ") || s.startsWith("yield ") ||
    s.startsWith("if (") || s.startsWith("if(") ||
    s.startsWith("} else") || s.startsWith("else {") || s.startsWith("else if") ||
    s.startsWith("for (") || s.startsWith("for(") ||
    s.startsWith("while (") || s.startsWith("switch (") ||
    s.startsWith("try {") || s.startsWith("catch ") || s.startsWith("finally {") ||
    s.startsWith("System.") || s.startsWith("console.") ||
    s.startsWith("fmt.") || s.startsWith("print(") || s.startsWith("printf(") ||
    s.startsWith("package ") || s.startsWith("#include") ||
    s === "{" || s === "}" || s === "};" || s === "}," || s === "..." ||
    s.startsWith("type ") || s.startsWith("struct ") ||
    s.startsWith("go ") || s.startsWith("chan ") ||
    /^[a-z_]\w+\s*[\(=]/.test(s) ||
    /^[A-Z]\w+\./.test(s)
  );
}

/**
 * Converts the raw plain-text notes format into proper Markdown.
 * Detects code blocks (preceded by a language-label line), Deep Dive headings,
 * emoji callouts, and bold inline labels.
 */
export function preprocessNoteContent(raw: string): string {
  const lines = raw.split("\n");
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Pass blank lines through
    if (!trimmed) { out.push(""); i++; continue; }

    // ── Language label → fenced code block ──────────────────────────────────
    if (trimmed in CODE_LANG_MAP) {
      const nxt = findNextNonBlank(lines, i + 1);
      if (nxt !== null && isCodeishLine(lines[nxt])) {
        const langKey = CODE_LANG_MAP[trimmed];
        out.push("");
        out.push("```" + langKey);
        i++; // consume the label line
        while (i < lines.length) {
          const cl = lines[i].trimEnd();
          const ct = cl.trim();
          if (!ct) {
            // Blank inside code – look ahead to decide if block ends
            const nxtNB = findNextNonBlank(lines, i + 1);
            if (nxtNB === null) { i++; break; }
            const nxtTrim = lines[nxtNB].trim();
            // End block if next non-blank is prose, a heading, callout, or another language label
            const endBlock =
              (nxtTrim in CODE_LANG_MAP) ||
              nxtTrim.startsWith("Deep Dive:") ||
              /^[⚠💡📌🔍\u26a0]/.test(nxtTrim) ||
              nxtTrim.startsWith("##") ||
              nxtTrim.startsWith("> ") ||
              nxtTrim.startsWith("- **") ||
              (!isCodeishLine(lines[nxtNB]) && /^[A-Z]/.test(nxtTrim) && nxtTrim.length > 15);
            if (endBlock) { i++; break; }
            out.push(""); i++;
          } else {
            // Non-blank line: if it's clearly prose/markdown, terminate the block immediately
            // (handles cases where there's no blank line between code and prose)
            const isProse =
              (ct in CODE_LANG_MAP) ||
              ct.startsWith("Deep Dive:") ||
              /^[⚠💡📌🔍\u26a0]/.test(ct) ||
              ct.startsWith("- **") ||
              (!isCodeishLine(cl) && /^[A-Z][a-z]/.test(ct) && ct.length > 20 && !ct.endsWith("{") && !ct.endsWith("("));
            if (isProse) { break; } // don't advance i — let main loop reprocess this line
            out.push(cl); i++;
          }
        }
        out.push("```");
        out.push("");
        continue;
      }
    }

    // ── Deep Dive: heading → ## ─────────────────────────────────────────────
    if (/^Deep Dive:/.test(trimmed)) {
      out.push("");
      out.push(`## 🔍 ${trimmed}`);
      out.push("");
      i++; continue;
    }

    // ── Emoji callout lines → blockquote ────────────────────────────────────
    if (/^[⚠💡📌🔍]/.test(trimmed) || /^\u26a0/.test(trimmed)) {
      out.push("");
      out.push(`> ${trimmed}`);
      out.push("");
      i++; continue;
    }

    // ── Bold inline labels (Definition:, When to use:, Tradeoffs:, …) ───────
    const labelMatch = /^(Interview Patterns|When to use|Tradeoffs?|How it works|Definition|When it happens|Benefits?|How it Works):\s*(.*)/.exec(trimmed);
    if (labelMatch) {
      const rest = labelMatch[2].trim();
      out.push(rest ? `**${labelMatch[1]}:** ${rest}` : `**${labelMatch[1]}:**`);
      i++; continue;
    }

    // ── Definition bullet: "Term: Long description." → "- **Term:** desc" ───
    // Matches patterns like "Simplex: Communication is...", "SYN: Client sends..."
    // "OSPF (Open Shortest Path First): An Interior Gateway Protocol..."
    const colonPos = trimmed.indexOf(": ");
    if (
      colonPos > 1 &&
      colonPos <= 60 &&
      trimmed.length - colonPos > 15 &&
      !trimmed.startsWith("Deep Dive:") &&
      !isCodeishLine(line)
    ) {
      const term = trimmed.slice(0, colonPos);
      const desc = trimmed.slice(colonPos + 2);
      // Term must start with capital, contain no periods (not a sentence fragment)
      if (!term.includes(".") && /^[A-Z]/.test(term)) {
        out.push(`- **${term}:** ${desc}`);
        i++; continue;
      }
    }

    // ── Short title-case standalone lines → ### sub-heading ─────────────────
    // Must be ≤60 chars, title-case or ALL-CAPS label, no trailing punctuation like '.' or ','
    if (
      trimmed.length <= 70 &&
      trimmed.length >= 4 &&
      /^[A-Z]/.test(trimmed) &&
      !/[.,;?!]$/.test(trimmed) &&
      !trimmed.includes(". ") &&       // not a sentence
      !/^\d/.test(trimmed) &&          // not a numbered item
      !/^(The |A |An |In |On |At |By |If |When |For |To |This |That |These |With |Without )/.test(trimmed) &&
      // Followed by a blank line or another short line (i.e., not mid-paragraph)
      (i + 1 >= lines.length || lines[i + 1].trim() === "" || lines[i + 1].trim().length < 80)
    ) {
      out.push("");
      out.push(`### ${trimmed}`);
      out.push("");
      i++; continue;
    }

    out.push(line);
    i++;
  }

  return out.join("\n");
}

// ---------------------------------------------------------------------------
// Section parsing
// ---------------------------------------------------------------------------

export interface NoteSection {
  number: number;
  /** Full title e.g. "5. Functions / Methods" */
  title: string;
  /** Label without number prefix e.g. "Functions / Methods" */
  label: string;
  content: string;
}

/**
 * Splits note content into numbered sections like "1. Programming Fundamentals",
 * "5. Functions / Methods", "15 Debugging, Testing & Optimization", etc.
 * Returns [] if fewer than 3 sections are detected (caller should show full content).
 */
export function parseNoteSections(content: string): NoteSection[] {
  const lines = content.split("\n");
  // Matches only lines that strictly start with a number: "1. Title" or "1 Title"
  const headerPattern = /^(\d{1,2})[.\s]\s*([A-Z&\/(][^\n]{3,80})$/;

  const headers: Array<{ lineIdx: number; num: number; label: string }> = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const m = headerPattern.exec(line);
    if (!m) continue;
    const num = parseInt(m[1], 10);
    // Strip any accidental leading "N. " that leaked into the label
    const label = m[2].trim().replace(/^\d+[.\s]\s*/, "").replace(/[,.]$/, "");
    if (num < 1 || num > 50) continue;
    // Skip obvious code lines
    if (/^(def |function |class |import |return |print |if |for |while |var |let |const |public |private |#)/.test(label)) continue;
    // Must start with uppercase letter or &
    if (!/^[A-Z&(\/]/.test(label)) continue;
    // Avoid duplicate section numbers
    if (headers.some((h) => h.num === num)) continue;
    headers.push({ lineIdx: i, num, label });
  }

  if (headers.length < 3) return [];

  // Sort sidebar by section number regardless of file order
  const sortedHeaders = [...headers].sort((a, b) => a.num - b.num);

  return sortedHeaders.map((header) => {
    const startLine = header.lineIdx + 1;
    // Content ends at the next header line in file order
    const nextInFile = headers
      .filter((h) => h.lineIdx > header.lineIdx)
      .sort((a, b) => a.lineIdx - b.lineIdx)[0];
    const endLine = nextInFile ? nextInFile.lineIdx : lines.length;
    const sectionContent = lines.slice(startLine, endLine).join("\n").trim();
    return {
      number: header.num,
      title: `${header.num}. ${header.label}`,
      label: header.label,
      content: sectionContent,
    };
  });
}

/** Fetches content for a bucket filename (e.g. "2. programming.txt") via public URL. */
export async function getNoteByFile(file: string): Promise<string | null> {
  const supabase = getSupabaseClient();
  if (!supabase) return null;

  const { data: { publicUrl } } = supabase.storage.from(BUCKET).getPublicUrl(file);
  try {
    const res = await fetch(publicUrl);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}
