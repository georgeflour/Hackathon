"use client";

import { useState } from "react";
import UploadForm      from "@/components/UploadForm";
import ExtractedPreview from "@/components/ExtractedPreview";
import MatchPanel       from "@/components/MatchPanel";
import AnswerPanel      from "@/components/AnswerPanel";
import { uploadBill, matchBill, explainBill } from "@/lib/api";

const DEFAULT_QUESTION = "Why is my bill higher this month?";

export default function Home() {
  const [extracted,   setExtracted]   = useState<Record<string, unknown> | null>(null);
  const [matchResult, setMatchResult] = useState<Record<string, unknown> | null>(null);
  const [answer,      setAnswer]      = useState<Record<string, unknown> | null>(null);
  const [question,    setQuestion]    = useState(DEFAULT_QUESTION);
  const [loading,     setLoading]     = useState<string | null>(null);
  const [error,       setError]       = useState<string | null>(null);

  async function handleUpload(file: File) {
    setError(null);
    setExtracted(null);
    setMatchResult(null);
    setAnswer(null);

    try {
      setLoading("⚙️  Agent 1 — Extracting bill data…");
      const ext = await uploadBill(file);
      setExtracted(ext);

      setLoading("🔍  Agent 2 — Matching customer in DWH…");
      const match = await matchBill(ext);
      setMatchResult(match);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }

  async function handleExplain() {
    if (!extracted || !matchResult) return;
    setError(null);
    setAnswer(null);

    try {
      setLoading("✨  Agent 3 — Generating grounded answer…");
      const result = await explainBill(extracted, matchResult, question);
      setAnswer(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload */}
      <UploadForm onUpload={handleUpload} />

      {/* Loading indicator */}
      {loading && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700 animate-pulse">
          <span className="text-lg">🔄</span>
          {loading}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* Agent 1 output */}
      {extracted && <ExtractedPreview extracted={extracted} />}

      {/* Agent 2 output + question input */}
      {matchResult && (
        <MatchPanel
          matchResult={matchResult}
          question={question}
          onQuestionChange={setQuestion}
          onExplain={handleExplain}
          loading={loading !== null}
        />
      )}

      {/* Agent 3 output */}
      {answer && <AnswerPanel answer={answer} />}
    </div>
  );
}

