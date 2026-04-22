import { getSupabaseClient } from "./supabase";

const BUCKET = "Notes";

// Display-name overrides keyed by stripped slug (no number prefix, no extension)
const labelOverrides: Record<string, string> = {
  "programming": "Programming (C++/Java/Python)",
  "ai-ml-data-analytics": "AI / Machine Learning and Data Analytics",
  "cloud-computing": "Cloud Computing",
  "cybersecurity": "Cybersecurity",
  "software-engineering": "Software Engineering",
  "web-development": "Web Development",
  "data-structures-algorithms": "Data Structures and Algorithms",
  "databases": "Databases",
  "operating-systems": "Operating Systems",
  "problem-solving": "Problem Solving and Analytical Skills",
  "computer-networks-cloud-computing": "Computer Networks and Cloud Computing",
};

/** Strip leading "N. " prefix and file extension → lookup key. */
function toKey(name: string): string {
  return name.replace(/^\d+\.\s*/, "").replace(/\.[^/.]+$/, "").trim();
}

async function probeExists(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { method: "HEAD" });
    return res.ok;
  } catch {
    return false;
  }
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
  const { data } = await supabase.storage.from(BUCKET).list("", { limit: 100 });
  if (data && data.length > 0) {
    return data
      .filter((f) => /\.(md|txt)$/i.test(f.name))
      .map((f) => ({ file: f.name, label: labelOverrides[toKey(f.name)] ?? toKey(f.name) }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  // Fallback: probe public URLs for all known slug × extension × number-prefix combos.
  // This finds files like "2. programming.txt", "programming.md", "databases.txt", etc.
  const base = supabase.storage.from(BUCKET).getPublicUrl("x").data.publicUrl.replace(/\/x$/, "");
  const slugs = Object.keys(labelOverrides);
  const exts = [".txt", ".md"];

  const candidates: string[] = [];
  for (const slug of slugs) {
    for (const ext of exts) {
      candidates.push(`${slug}${ext}`);                    // plain: programming.txt
      for (let n = 1; n <= 12; n++) {
        candidates.push(`${n}. ${slug}${ext}`);            // numbered: 2. programming.txt
      }
    }
  }

  const results = await Promise.all(
    candidates.map(async (filename) => {
      const url = `${base}/${encodeURIComponent(filename)}`;
      const ok = await probeExists(url);
      if (!ok) return null;
      return { file: filename, label: labelOverrides[toKey(filename)] ?? toKey(filename) };
    })
  );

  // Deduplicate by label (prefer plain name over numbered if both somehow exist)
  const seen = new Set<string>();
  return results
    .filter((r): r is { file: string; label: string } => r !== null)
    .filter((r) => { if (seen.has(r.label)) return false; seen.add(r.label); return true; })
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
            // End block if next non-blank is prose (long cap sentence) or another language label
            const endBlock =
              (nxtTrim in CODE_LANG_MAP) ||
              (!isCodeishLine(lines[nxtNB]) && /^[A-Z][a-z]/.test(nxtTrim) && nxtTrim.length > 30);
            if (endBlock) { i++; break; }
            out.push(""); i++;
          } else {
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
    const labelMatch = /^(Interview Patterns|When to use|Tradeoffs|How it works|Definition|When it happens|Benefits|Tradeoffs|Benefit|How it Works):\s*(.*)/.exec(trimmed);
    if (labelMatch) {
      const rest = labelMatch[2].trim();
      out.push(rest ? `**${labelMatch[1]}:** ${rest}` : `**${labelMatch[1]}:**`);
      i++; continue;
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
  // Matches: optional leading whitespace, 1-2 digit number, period or space, space(s), then a capital-letter label
  const headerPattern = /^(\d{1,2})[.\s]\s*([A-Z&\/(][^\n]{3,80})$/;

  const headers: Array<{ lineIdx: number; num: number; label: string }> = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const m = headerPattern.exec(line);
    if (!m) continue;
    const num = parseInt(m[1], 10);
    const label = m[2].trim().replace(/[,.]$/, ""); // strip trailing punctuation
    if (num < 1 || num > 25) continue;
    // Skip obvious code lines
    if (/^(def |function |class |import |return |print |if |for |while |var |let |const |public |private |#)/.test(label)) continue;
    // Must start with uppercase letter or &
    if (!/^[A-Z&(\/]/.test(label)) continue;
    // Avoid duplicate section numbers
    if (headers.some((h) => h.num === num)) continue;
    headers.push({ lineIdx: i, num, label });
  }

  if (headers.length < 3) return [];

  return headers.map((header, i) => {
    const startLine = header.lineIdx + 1;
    const endLine = i + 1 < headers.length ? headers[i + 1].lineIdx : lines.length;
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
