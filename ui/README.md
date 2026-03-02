# Step 8 — Next.js Frontend

Location: `ui/`

This is the demo interface. It uploads a bill image, shows the extracted data, the match result, and the final grounded answer with citations.

---

## Setup

```bash
cd ui
npm install        # installs Next.js 14, React 18, Tailwind, TypeScript, axios
npm run dev        # → http://localhost:3000
```

`ui/.env.local` is already present:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Files to create

### Config files

| File | Notes |
|---|---|
| `ui/package.json` | next 14.x, react 18, tailwindcss, typescript, axios |
| `ui/next.config.js` | minimal `module.exports = {}` |
| `ui/tsconfig.json` | standard Next.js TS config with `@/*` path alias |
| `ui/tailwind.config.js` | content: `./src/**/*.{ts,tsx}` |
| `ui/postcss.config.js` | tailwindcss + autoprefixer |

### Source files

| File | Purpose |
|---|---|
| `ui/src/app/globals.css` | `@tailwind base/components/utilities` |
| `ui/src/app/layout.tsx` | root layout with `<header>` showing app name |
| `ui/src/app/page.tsx` | main page — orchestrates all components |
| `ui/src/lib/api.ts` | typed fetch wrappers for backend endpoints |
| `ui/src/components/UploadForm.tsx` | drag-and-drop + click upload widget |
| `ui/src/components/ExtractedPreview.tsx` | shows extracted bill fields + OCR confidence badge |
| `ui/src/components/MatchPanel.tsx` | shows match type badge, candidates, clarifying question, question input + "Generate" button |
| `ui/src/components/AnswerPanel.tsx` | shows answer text, citations list, confidence badge |

---

## `ui/src/lib/api.ts`

```typescript
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function uploadBill(file: File): Promise<Record<string, unknown>>
export async function matchBill(extracted: Record<string, unknown>): Promise<Record<string, unknown>>
export async function explainBill(
  extracted: Record<string, unknown>,
  matchResult: Record<string, unknown>,
  question: string,
): Promise<Record<string, unknown>>
```

Each function uses `fetch`. On non-OK response throw `new Error(res.statusText)`.
`uploadBill` sends `FormData` with field name `"file"`.
`matchBill` sends `{ extracted }` as JSON.
`explainBill` sends `{ extracted, match_result, question, retrieved_passages: [] }` as JSON.

---

## `ui/src/app/page.tsx`

This is a `"use client"` page. State:
- `extracted` — result of `/upload`
- `matchResult` — result of `/match`
- `answer` — result of `/explain`
- `question` — string, default `"Why is my bill higher this month?"`
- `loading` — string | null (shown as animated status line)
- `error` — string | null (shown as red alert)

### Flow

```
handleUpload(file):
  setLoading("Agent 1 — Extracting bill data…")
  extracted = await uploadBill(file)
  setLoading("Agent 2 — Matching customer…")
  match = await matchBill(extracted)
  setLoading(null)

handleExplain():
  setLoading("Agent 3 — Generating grounded answer…")
  result = await explainBill(extracted, matchResult, question)
  setLoading(null)
```

Render order: `<UploadForm>` → loading line → error → `<ExtractedPreview>` → `<MatchPanel>` → `<AnswerPanel>`.

---

## `ui/src/components/UploadForm.tsx`

- A styled `div` with `border-dashed` that accepts drag-and-drop and click.
- Hidden `<input type="file" accept="image/*,.pdf">`.
- On file selected → call `props.onUpload(file)`.

Props:
```typescript
interface Props { onUpload: (file: File) => void }
```

---

## `ui/src/components/ExtractedPreview.tsx`

Props:
```typescript
interface Props { extracted: Record<string, unknown> }
```

Display:
- Section title: `📋 Extracted Bill Data`
- OCR confidence badge: green ≥ 85%, yellow ≥ 60%, red otherwise
- Fields: Account No., Customer, Bill No., Period, Total Due, Meters
- Line items table with columns: Description, kWh, Amount

---

## `ui/src/components/MatchPanel.tsx`

Props:
```typescript
interface Props {
  matchResult: Record<string, unknown>
  question: string
  onQuestionChange: (q: string) => void
  onExplain: () => void
}
```

Display:
- Section title: `🔍 Customer Match`
- Match type badge: green for `exact`, blue for `fuzzy_high`, yellow for `fuzzy_ambiguous`, red for `none`
- If matched: show customer ID + score
- If candidates > 1: show candidate list with scores
- If `clarifying_question`: show it in a yellow info box
- If `none`: show a red notice that only general knowledge will be used
- `<textarea>` for the question (pre-filled with default)
- `✨ Generate Explanation` button that calls `onExplain`

---

## `ui/src/components/AnswerPanel.tsx`

Props:
```typescript
interface Props { answer: Record<string, unknown> }
```

Display:
- Section title: `💡 AI Explanation`
- Confidence badge: green `High`, yellow `Medium`, red `Low` + numeric score
- Answer text in a `<p>` with `whitespace-pre-wrap`
- Sources list: `📎 {doc_id}, page {page}` — optionally show snippet in italic

---

## Styling rules

- Use Tailwind utility classes only — no external component libraries.
- Keep the layout single-column, max-width `max-w-3xl mx-auto`.
- Cards: `bg-white rounded-xl border border-gray-200 p-5`.
- Badges: `text-xs px-2 py-1 rounded-full font-medium`.
- Primary button: `bg-blue-600 hover:bg-blue-700 text-white`.

---

## Validation checklist

- [ ] `npm run dev` starts without errors
- [ ] `npm run build` completes without TypeScript errors
- [ ] Upload form accepts image files and shows loading state
- [ ] ExtractedPreview shows OCR confidence badge
- [ ] MatchPanel shows correct badge colour per match type
- [ ] Clarifying question is visible when `match_type == "fuzzy_ambiguous"`
- [ ] AnswerPanel shows citations list
- [ ] No `any` TypeScript types (use `Record<string, unknown>` or proper interfaces)

---

## Demo script — run all three scenarios

### Scenario 1 — Exact match
Upload `X51008099047.jpg` from the repo root. Expect: match type `exact`, high confidence answer with tariff citation.

### Scenario 2 — Ambiguous match
Upload `X51009453729.jpg`. If match is ambiguous, the clarifying question box appears. Select the correct customer and click Generate.

### Scenario 3 — No match
Upload `X51009568881.jpg`. If no match, the system answers from the general knowledge corpus only.

---

## Done! Full pipeline is complete.

Run the full test suite:
```bash
source .venv/bin/activate
python -m pytest src -v
```

