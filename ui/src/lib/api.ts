const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
async function apiFetch(path: string, init?: RequestInit): Promise<Record<string, unknown>> {
  const res = await fetch(`${API}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || res.statusText);
  }
  return res.json();
}
export async function uploadBill(files: File[], init?: RequestInit): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append("file_front", files[0]);
  if (files[1]) form.append("file_back", files[1]);
  return apiFetch("/upload", { ...init, method: "POST", body: form });
}
export async function matchBill(
  extracted: Record<string, unknown>,
  init?: RequestInit
): Promise<Record<string, unknown>> {
  return apiFetch("/match", {
    ...init,
    method: "POST",
    headers: { "Content-Type": "application/json", ...init?.headers },
    body: JSON.stringify({ extracted }),
  });
}
export async function explainBill(
  extracted: Record<string, unknown>,
  matchResult: Record<string, unknown>,
  question: string,
  init?: RequestInit
): Promise<Record<string, unknown>> {
  return apiFetch("/explain", {
    ...init,
    method: "POST",
    headers: { "Content-Type": "application/json", ...init?.headers },
    body: JSON.stringify({
      extracted,
      match_result: matchResult,
      question,
      retrieved_passages: [],
    }),
  });
}
export async function chatWithAssistant(
  question: string,
  ragContext: string = "",
  sqlContext: string = ""
): Promise<Record<string, unknown>> {
  return apiFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      rag_context: ragContext,
      sql_context: sqlContext,
    }),
  });
}
