interface Props {
  matchResult: Record<string, unknown>;
  question: string;
  onQuestionChange: (q: string) => void;
  onExplain: () => void;
  loading: boolean;
}

const BADGE: Record<string, string> = {
  exact:            "bg-green-100 text-green-700",
  fuzzy_high:       "bg-blue-100 text-blue-700",
  fuzzy_ambiguous:  "bg-yellow-100 text-yellow-700",
  none:             "bg-red-100 text-red-700",
};

const LABEL: Record<string, string> = {
  exact:            "✅ Exact match",
  fuzzy_high:       "🔵 High-confidence match",
  fuzzy_ambiguous:  "⚠️ Ambiguous match",
  none:             "❌ No match",
};

type Candidate = { customer_id: string; customer_name: string; score: number; match_field: string };

export default function MatchPanel({ matchResult, question, onQuestionChange, onExplain, loading }: Props) {
  const matchType = (matchResult.match_type as string) ?? "none";
  const custId    = matchResult.matched_customer_id as string | null;
  const score     = matchResult.score as number;
  const candidates = (matchResult.candidates as Candidate[]) ?? [];
  const clarQ     = matchResult.clarifying_question as string | null;
  const ctx       = matchResult.customer_context as Record<string, unknown> | undefined;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800 mb-4">🔍 Customer Match</h2>

      {/* Badge */}
      <div className="flex items-center gap-3 mb-4">
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${BADGE[matchType] ?? BADGE.none}`}>
          {LABEL[matchType] ?? matchType}
        </span>
        {custId && (
          <span className="text-sm text-gray-600">
            <span className="font-mono text-gray-800">{custId}</span>
            <span className="text-gray-400 ml-2">score {(score * 100).toFixed(0)}%</span>
          </span>
        )}
      </div>

      {/* Customer context snapshot */}
      {ctx && (
        <div className="bg-gray-50 rounded-lg p-3 text-sm mb-4">
          <p className="font-medium text-gray-700">{String(ctx.customer_name ?? "")}</p>
          <p className="text-gray-500">{String(ctx.segment ?? "")} · Tariff {String(ctx.active_tariff ?? "")} · Avg {String(ctx.avg_kwh_6m ?? "?")} kWh/mo</p>
        </div>
      )}

      {/* Candidates (ambiguous) */}
      {candidates.length > 1 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Candidates</p>
          <ul className="space-y-1">
            {candidates.map((c) => (
              <li key={c.customer_id} className="flex justify-between text-sm">
                <span className="text-gray-800">{c.customer_name} <span className="text-gray-400 font-mono text-xs">({c.customer_id})</span></span>
                <span className="text-gray-500">{(c.score * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Clarifying question */}
      {clarQ && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800 mb-4 whitespace-pre-wrap">
          {clarQ}
        </div>
      )}

      {/* No match warning */}
      {matchType === "none" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 mb-4">
          No customer found in the database. The answer will be based on the general knowledge corpus only.
        </div>
      )}

      {/* Question + Generate button */}
      <div className="mt-2">
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
          Your question
        </label>
        <textarea
          className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          rows={3}
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
        />
        <button
          onClick={onExplain}
          disabled={loading}
          className="mt-3 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
        >
          {loading ? "Generating…" : "✨ Generate Explanation"}
        </button>
      </div>
    </div>
  );
}

