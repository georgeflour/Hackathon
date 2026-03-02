interface Props { extracted: Record<string, unknown> }

function field(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "object" && v !== null && "value" in v) return String((v as Record<string, unknown>).value ?? "—");
  return String(v);
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const cls = score >= 0.85 ? "bg-green-100 text-green-700" : score >= 0.60 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
  return <span className={`text-xs px-2 py-1 rounded-full font-medium ${cls}`}>OCR {pct}%</span>;
}

export default function ExtractedPreview({ extracted }: Props) {
  const conf  = (extracted.ocr_confidence as number) ?? 0;
  const acct  = extracted.account_number as Record<string, unknown>;
  const name  = extracted.customer_name  as Record<string, unknown>;
  const bill  = extracted.bill_number    as Record<string, unknown>;
  const period = extracted.service_period as Record<string, unknown> | undefined;
  const total = extracted.total_due as Record<string, unknown> | undefined;
  const meters = (extracted.meter_ids as string[]) ?? [];
  const items  = (extracted.line_items as Record<string, unknown>[]) ?? [];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-800">📋 Extracted Bill Data</h2>
        <ConfidenceBadge score={conf} />
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-gray-500">Account No.</dt>
        <dd className="text-gray-900 font-mono">{field(acct)}</dd>

        <dt className="text-gray-500">Customer</dt>
        <dd className="text-gray-900">{field(name)}</dd>

        <dt className="text-gray-500">Bill No.</dt>
        <dd className="text-gray-900 font-mono">{field(bill)}</dd>

        <dt className="text-gray-500">Period</dt>
        <dd className="text-gray-900">
          {String(period?.start ?? "?")} → {String(period?.end ?? "?")}
        </dd>

        <dt className="text-gray-500">Total Due</dt>
        <dd className="text-gray-900 font-semibold">
          {field(total)} {(total?.currency as string) ?? "EUR"}
        </dd>

        <dt className="text-gray-500">Meter(s)</dt>
        <dd className="text-gray-900 font-mono">{meters.join(", ") || "—"}</dd>

        <dt className="text-gray-500">Tariff</dt>
        <dd className="text-gray-900">{String(extracted.tariff_code ?? "—")}</dd>
      </dl>

      {items.length > 0 && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Line Items</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-100">
                <th className="pb-1 font-medium">Description</th>
                <th className="pb-1 font-medium text-right">kWh</th>
                <th className="pb-1 font-medium text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((li, i) => (
                <tr key={i} className="border-b border-gray-50">
                  <td className="py-1 capitalize">{String(li.description ?? "")}</td>
                  <td className="py-1 text-right text-gray-600">{li.quantity_kwh != null ? String(li.quantity_kwh) : "—"}</td>
                  <td className="py-1 text-right font-mono">{li.amount != null ? `${li.amount} EUR` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

