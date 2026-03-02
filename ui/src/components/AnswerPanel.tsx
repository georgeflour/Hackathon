interface Citation { doc_id: string; page: number; snippet?: string }
interface Props { answer: Record<string, unknown> }

const CONF_BADGE: Record<string, string> = {
  High:   "bg-green-100 text-green-700",
  Medium: "bg-yellow-100 text-yellow-700",
  Low:    "bg-red-100 text-red-700",
};

export default function AnswerPanel({ answer }: Props) {
  const text         = answer.answer       as string;
  const label        = answer.confidence_label as string;
  const score        = answer.confidence_score as number;
  const citations    = (answer.citations    as Citation[]) ?? [];
  const unsupported  = (answer.unsupported_claims as string[]) ?? [];
  const passages     = (answer.retrieved_passages as Record<string, unknown>[]) ?? [];

  // @ts-ignore
    // @ts-ignore
    return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-800">💡 AI Explanation</h2>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${CONF_BADGE[label] ?? CONF_BADGE.Low}`}>
            {label} confidence
          </span>
          <span className="text-xs text-gray-400">{(score * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Answer text */}
      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{text}</p>

      {/* Unsupported claims warning */}
      {unsupported.length > 0 && (
        <div className="mt-4 bg-orange-50 border border-orange-200 rounded-lg p-3 text-xs text-orange-800">
          <p className="font-semibold mb-1">⚠️ Unverified claims (manual review recommended):</p>
          <ul className="list-disc list-inside space-y-0.5">
            {unsupported.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div className="mt-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Sources</h3>
          <ul className="space-y-2">
            {citations.map((c, i) => (
              <li key={i} className="text-sm flex gap-2">
                <span className="text-blue-500 shrink-0">📎</span>
                <span>
                  <span className="font-mono text-gray-700">{c.doc_id}</span>
                  <span className="text-gray-400">, page {c.page}</span>
                  {c.snippet && <span className="block text-xs text-gray-400 italic mt-0.5">{c.snippet}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Retrieved passages (collapsed) */}
      {passages.length > 0 && (
        <details className="mt-5">
          <summary className="text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer hover:text-gray-700">
            Retrieved passages ({passages.length})
          </summary>
          <ul className="mt-2 space-y-3">
            {passages.map((p, i) => (
              <li key={i} className="border border-gray-100 rounded-lg p-3">
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-mono text-gray-600">{String(p.doc_id)} p{String(p.page)}</span>
                  <span className="text-gray-400">score {((p.final_score as number) * 100).toFixed(0)}%</span>
                </div>
                <p className="text-xs text-gray-500 italic">{String(p.text_snippet ?? "").slice(0, 200)}…</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

