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
  sqlContext: string = "",
  init?: RequestInit
): Promise<Record<string, unknown>> {
  return apiFetch("/chat", {
    ...init,
    method: "POST",
    headers: { "Content-Type": "application/json", ...init?.headers },
    body: JSON.stringify({
      question,
      rag_context: ragContext,
      sql_context: sqlContext,
    }),
  });
}

// ─── Chat History Methods ──────────────────────────────────────────────

export async function getSessions(): Promise<Record<string, any>[]> {
  const data = await apiFetch("/history/sessions");
  return (data.sessions as Record<string, any>[]) || [];
}

export async function createSession(title: string = "New Chat"): Promise<string> {
  const data = await apiFetch("/history/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return data.session_id as string;
}

export async function getSessionMessages(sessionId: string): Promise<Record<string, any>[]> {
  const data = await apiFetch(`/history/sessions/${sessionId}/messages`);
  return (data.messages as Record<string, any>[]) || [];
}

export async function saveMessage(sessionId: string, role: string, content: string, imageUrls?: string[]): Promise<string> {
  const data = await apiFetch(`/history/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, content, image_urls: imageUrls || [] }),
  });
  return data.message_id as string;
}

export async function renameSession(sessionId: string, newTitle: string): Promise<void> {
  await apiFetch(`/history/sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: newTitle }),
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch(`/history/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

