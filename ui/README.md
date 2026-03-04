# DEH AI Billing Agent — UI

A minimalist Next.js 14 chat interface for the DEH Smart Bill Assistant. Users can upload an electricity bill (image or PDF), have it automatically analysed and matched against the DWH, and then ask natural-language questions about it — powered by a RAG backend.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [Next.js 14](https://nextjs.org/) (App Router) |
| Language | TypeScript |
| Styling | Vanilla CSS (`globals.css`) + inline styles |
| HTTP Client | Native `fetch` via `src/lib/api.ts` |

---

## Folder Structure

```
ui/
├── public/
│   └── bot-picture.png        # DEH logo shown in header & chat bubbles
│
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout (font, metadata)
│   │   ├── page.tsx           # Main chat page — all UI logic lives here
│   │   └── globals.css        # Global styles, animations, CSS variables
│   │
│   └── lib/
│       └── api.ts             # API client (upload / match / explain)
│
├── next.config.js
├── package.json
└── tsconfig.json
```

### Key Files

#### `src/app/page.tsx`
The entire chat application in a single file:
- **`DEHLogo`** — renders the DEH logo image from `/public`
- **`getGreeting()`** — returns a time-aware greeting (*Good morning / afternoon / evening / Hello there, Night Owl!*)
- **`EmptyState`** — centered greeting shown when the chat is empty (ChatGPT-style)
- **`Bubble`** — renders individual chat messages (user / assistant / system)
- **`DataCard`** — structured key-value card for extracted bill data and matched customer data
- **`Home`** — root component managing all state and the three-agent flow

#### `src/lib/api.ts`
Thin wrapper around `fetch` pointing to the backend (`NEXT_PUBLIC_API_URL`, defaults to `http://localhost:8000`):

| Function | Endpoint | Description |
|---|---|---|
| `uploadBill(file)` | `POST /upload` | Agent 1 — extracts bill fields via Vision |
| `matchBill(extracted)` | `POST /match` | Agent 2 — matches customer in DWH |
| `explainBill(extracted, match, question)` | `POST /explain` | Agent 3 — RAG answer generation |

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- The backend API running (see root-level README)

### Install dependencies

```bash
cd ui
npm install
```

### Run in development

```bash
npm run dev
```

The app will be available at **http://localhost:3000**.

### Environment variables

Create a `.env.local` file if the backend runs on a different host/port:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Build for production

```bash
npm run build
npm run start
```

---

## Agent Flow

```
User uploads bill
      │
      ▼
Agent 1 — Vision extraction  (POST /upload)
      │  returns: extracted bill fields
      ▼
Agent 2 — DWH matching       (POST /match)
      │  returns: customer record
      ▼
User asks a question
      │
      ▼
Agent 3 — RAG answer         (POST /explain)
           returns: natural-language explanation
```

---

*Hack to the Future © 2025*
