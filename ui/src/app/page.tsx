"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { uploadBill } from "@/lib/api";

/* ─── types ──────────────────────────────────────────────────────────── */
type Role = "user" | "assistant" | "system";
interface Message {
  id: string;
  role: Role;
  content: string;
  imageUrls?: string[];          // blob preview URLs for image attachments
  // optional structured payload after agent runs
  stage?: "upload" | "match" | "answer";
  payload?: Record<string, unknown>;
  attachments?: File[];
}

/* ─── helpers ────────────────────────────────────────────────────────── */
function uid() {
  return Math.random().toString(36).slice(2);
}

function DEHLogo({ size = 38 }: { size?: number }) {
  return (
    <Image
      src="/bot-picture.png"
      alt="ΔΕΗ Logo"
      width={size}
      height={size}
      style={{ borderRadius: 8, objectFit: "contain" }}
      priority
    />
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good morning.";
  if (hour >= 12 && hour < 17) return "Good afternoon.";
  if (hour >= 17 && hour < 21) return "Good evening.";
  return "Hello there, Night Owl!";
}

/* ─── empty state (centered greeting) ───────────────────────────────── */
function EmptyState() {
  return (
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
      padding: "0 16px",
      pointerEvents: "none",
    }}>
      <div style={{
        fontSize: 36,
        fontWeight: 700,
        color: "#111827",
        letterSpacing: "-0.03em",
        lineHeight: 1.1,
        textAlign: "center",
      }}>
        {getGreeting()}
      </div>
      <div style={{
        fontSize: 15,
        color: "#9CA3AF",
        fontWeight: 400,
        textAlign: "center",
      }}>
        How can I help you today?
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 2px" }}>
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </span>
  );
}

/* ─── card for extracted / match data ───────────────────────────────── */
function DataCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  const rows = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== "");
  return (
    <div style={{
      background: "rgba(0,163,224,0.05)",
      border: "1px solid rgba(0,163,224,0.2)",
      borderRadius: 12,
      padding: "14px 16px",
      marginTop: 10,
      fontSize: 13,
    }}>
      <div style={{ color: "#00A3E0", fontWeight: 600, marginBottom: 8, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</div>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 12px" }}>
        {rows.slice(0, 10).map(([k, v]) => (
          <>
            <span key={k + "-k"} style={{ color: "#9CA3AF", whiteSpace: "nowrap" }}>{k.replace(/_/g, " ")}</span>
            <span key={k + "-v"} style={{ color: "#111827", wordBreak: "break-all" }}>{String(v)}</span>
          </>
        ))}
      </div>
    </div>
  );
}

/* ─── individual chat bubble ─────────────────────────────────────────── */
function Bubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";

  if (isSystem) {
    return (
      <div className="fade-up" style={{ textAlign: "center", padding: "4px 0" }}>
        <span style={{
          fontSize: 11,
          color: "#9CA3AF",
          background: "rgba(0,0,0,0.04)",
          borderRadius: 20,
          padding: "2px 10px",
          letterSpacing: "0.04em",
        }}>{msg.content}</span>
      </div>
    );
  }

  return (
    <div className="fade-up" style={{
      display: "flex",
      flexDirection: isUser ? "row-reverse" : "row",
      alignItems: "flex-end",
      gap: 10,
    }}>
      {/* Avatar */}
      {!isUser && (
        <div style={{ flexShrink: 0, marginBottom: 2 }}>
          <DEHLogo size={32} />
        </div>
      )}

      <div style={{
        maxWidth: "75%",
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        gap: 4,
      }}>
        <div style={{
          background: isUser
            ? "linear-gradient(135deg, #c8ecf8 0%, #e8f7fd 100%)"
            : "#FFFFFF",
          boxShadow: isUser ? "0 2px 8px rgba(0,163,224,0.12)" : "0 2px 10px rgba(0,0,0,0.05)",
          borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
          padding: msg.imageUrls?.length ? "8px" : "10px 14px",
          lineHeight: 1.6,
          fontSize: 14,
          color: "#111827",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          overflow: "hidden",
        }}>
          {/* Image thumbnails */}
          {msg.imageUrls && msg.imageUrls.length > 0 && (
            <div style={{
              display: "grid",
              gridTemplateColumns: msg.imageUrls.length === 1 ? "1fr" : "1fr 1fr",
              gap: 4,
              marginBottom: msg.content ? 8 : 0,
            }}>
              {msg.imageUrls.map((url, i) => (
                <img
                  key={i}
                  src={url}
                  alt={`attachment ${i + 1}`}
                  style={{
                    width: "100%",
                    maxWidth: 240,
                    borderRadius: 10,
                    objectFit: "cover",
                    display: "block",
                  }}
                />
              ))}
            </div>
          )}
          {/* Text content */}
          {msg.content && (msg.content === "…" ? <TypingDots /> : <span style={{ padding: msg.imageUrls?.length ? "0 6px 4px" : undefined, display: "block" }}>{msg.content}</span>)}
        </div>

        {/* Optional structured payload */}
        {msg.payload && msg.stage === "upload" && (
          <DataCard title="Bill Extracted" data={msg.payload as Record<string, unknown>} />
        )}
        {msg.payload && msg.stage === "match" && (
          <DataCard title="Customer Matched" data={msg.payload as Record<string, unknown>} />
        )}
      </div>

    </div>
  );
}

/* ─── main page ──────────────────────────────────────────────────────── */
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [extracted, setExtracted] = useState<Record<string, unknown> | null>(null);
  const [matchResult, setMatchResult] = useState<Record<string, unknown> | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // History state
  const [sessions, setSessions] = useState<{ id: string; title: string; created_at: string }[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // History Edit State
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editSessionTitle, setEditSessionTitle] = useState("");


  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    import("@/lib/api").then((api) => {
      api.getSessions().then((data) => setSessions(data as any)).catch(console.error);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  function handleRestart() {
    setMessages([]);
    setInput("");
    setFiles([]);
    setExtracted(null);
    setMatchResult(null);
    setIsTyping(false);
    setCurrentSessionId(null);
    if (fileRef.current) {
      fileRef.current.value = "";
    }
    abortControllerRef.current?.abort();
  }

  async function loadSession(id: string) {
    handleRestart();
    setCurrentSessionId(id);
    try {
      const { getSessionMessages } = await import("@/lib/api");
      const msgs = await getSessionMessages(id);
      setMessages(msgs.map((m: any) => {
        let parsedImages = [];
        try {
          if (m.image_urls) parsedImages = JSON.parse(m.image_urls);
        } catch (e) {
          console.error("Failed to parse image_urls JSON", e);
        }
        return {
          id: m.id,
          role: m.role as Role,
          content: m.content,
          imageUrls: parsedImages.length > 0 ? parsedImages : undefined,
        };
      }));
    } catch (e) {
      console.error("Failed to load session", e);
    }
  }

  // Helper to convert File to Base64 string for persistence
  function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function handleDeleteSession(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    try {
      const { deleteSession, getSessions } = await import("@/lib/api");
      await deleteSession(id);
      if (currentSessionId === id) handleRestart();
      const updated = await getSessions();
      setSessions(updated as any);
    } catch (e) { console.error("Failed to delete session", e) }
  }

  async function handleRenameSession(e: React.MouseEvent | React.FormEvent, id: string) {
    if (e.type === 'submit') e.preventDefault();
    else e.stopPropagation();

    if (!editSessionTitle.trim()) {
      setEditingSessionId(null);
      return;
    }

    try {
      const { renameSession, getSessions } = await import("@/lib/api");
      await renameSession(id, editSessionTitle.trim());
      setEditingSessionId(null);
      const updated = await getSessions();
      setSessions(updated as any);
    } catch (e) { console.error("Failed to rename session", e) }
  }

  function addMsg(msg: Omit<Message, "id">) {
    const full: Message = { ...msg, id: uid() };
    setMessages((prev) => [...prev, full]);
    return full.id;
  }

  function updateMsg(id: string, patch: Partial<Message>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  function removeMsg(id: string) {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }

  /* ── attach file (no processing yet) ── */
  function handleFileChosen(chosen: File) {
    setFiles((prev) => [...prev, chosen]);
  }

  /* ── process files: upload only ── */
  async function processFiles(pending: File[]): Promise<Record<string, unknown> | null> {
    const typingId = addMsg({ role: "assistant", content: "…" });
    setIsTyping(true);

    abortControllerRef.current = new AbortController();

    try {
      const ext = await uploadBill(pending, { signal: abortControllerRef.current.signal });
      setExtracted(ext);
      updateMsg(typingId, {
        content: "I analysed your bill. Here are the extracted details:",
        stage: "upload",
        payload: ext,
      });
      return ext;
    } catch (e: any) {
      if (e.name === "AbortError") {
        removeMsg(typingId);
      } else {
        updateMsg(typingId, { content: `❌ ${String(e)}` });
      }
      return null;
    } finally {
      setIsTyping(false);
    }
  }

  /* ── send: handles files + optional question ── */
  async function handleSend() {
    const q = input.trim();
    const hasQuestion = q.length > 0;
    let pendingFiles = files;
    let localSessionId = currentSessionId;

    let currentExtracted = extracted;

    // 1. Recover files if we have no files, no extracted data, but a previous upload was aborted.
    if (pendingFiles.length === 0 && !currentExtracted) {
      // Look back for the last user message to see if it had attachments
      const lastUserMsg = messages.slice().reverse().find(m => m.role === "user");
      if (lastUserMsg?.attachments?.length) {
        pendingFiles = lastUserMsg.attachments;
      }
    }

    if (pendingFiles.length === 0 && !hasQuestion) return;

    setInput("");
    setIsTyping(true);

    // 2. Add user message
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));
    const nonImageFiles = files.filter((f) => !f.type.startsWith("image/"));
    const imageUrls = imageFiles.map((f) => URL.createObjectURL(f));
    const nonImageNames = nonImageFiles.length > 0 ? `📎 ${nonImageFiles.map((f) => f.name).join(", ")}` : "";
    const userContent = [nonImageNames, hasQuestion ? q : ""].filter(Boolean).join("\n");

    addMsg({
      role: "user",
      content: userContent,
      imageUrls: imageUrls.length > 0 ? imageUrls : undefined,
      attachments: files.length > 0 ? files : undefined
    });

    try {
      const imageBase64s = await Promise.all(imageFiles.map(f => fileToBase64(f)));

      const api = await import("@/lib/api");
      if (!localSessionId) {
        localSessionId = await api.createSession(userContent.slice(0, 30) || "File Upload");
        setCurrentSessionId(localSessionId);
        api.getSessions().then((data) => setSessions(data as any)).catch(console.error);
      }
      await api.saveMessage(localSessionId, "user", userContent, imageBase64s);
    } catch (e) { console.error(e); }

    setFiles([]); // clear attachment bar

    // 3. Process Files (Upload + Extract) if needed
    const isExplicitUpload = files.length > 0;
    if (isExplicitUpload || (pendingFiles.length > 0 && !currentExtracted)) {
      const ext = await processFiles(pendingFiles);
      if (!ext) {
        setIsTyping(false);
        return;
      }
      currentExtracted = ext;
    }

    // 4. Handle Questions
    if (hasQuestion) {
      abortControllerRef.current = new AbortController();
      const typingId = addMsg({ role: "assistant", content: "…" });
      setIsTyping(true);
      try {
        const currentMatch = matchResult || {};
        // Import and run chatWithAssistant instead of the older endpoint
        const { chatWithAssistant } = await import("@/lib/api");

        // You ideally would pass RAG context or SQL context here,
        // but for now we simply pass the question forwards. 
        const explanation = await chatWithAssistant(q, "", "", { signal: abortControllerRef.current.signal });
        const textAnswer = (explanation?.answer as string) || (explanation?.message as string) || "Done.";
        updateMsg(typingId, {
          content: textAnswer,
          stage: "answer",
          payload: explanation
        });

        if (localSessionId) {
          import("@/lib/api").then(api => api.saveMessage(localSessionId as string, "assistant", textAnswer)).catch(console.error);
        }
      } catch (e: any) {
        if (e.name === "AbortError") {
          removeMsg(typingId);
        } else {
          updateMsg(typingId, { content: `Assistant is not fully wired up for questions yet, but I received: "${q}"\n\n(Error: ${String(e)})` });
        }
      }
    } else if (pendingFiles.length > 0) {
      // Just uploaded files, no question
      addMsg({
        role: "assistant",
        content: "You can now ask me anything about your bill, e.g. \"Why is my bill higher than usual?\"",
      });
    }

    setIsTyping(false);
  }

  function handleStop() {
    abortControllerRef.current?.abort();
    setIsTyping(false);
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const dropped = Array.from(e.dataTransfer.files);
    dropped.forEach((f) => handleFileChosen(f));
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#F9FAFB" }}>
      {/* ── Sidebar ── */}
      <div style={{
        width: 260,
        background: "#FFFFFF",
        borderRight: "1px solid rgba(0,0,0,0.08)",
        display: isSidebarOpen ? "flex" : "none",
        flexDirection: "column",
        zIndex: 20,
      }}>
        <div style={{ padding: "16px", borderBottom: "1px solid rgba(0,0,0,0.08)", fontWeight: 600, color: "#111827", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            Previous Chats
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            style={{
              background: "transparent", border: "none", cursor: "pointer", color: "#9CA3AF",
              padding: "4px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s"
            }}
            onMouseOver={(e) => { e.currentTarget.style.color = "#4B5563"; e.currentTarget.style.background = "rgba(0,0,0,0.05)" }}
            onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent" }}
            title="Close Sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
          {sessions.map(s => (
            <div
              key={s.id}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 10px", background: currentSessionId === s.id ? "rgba(0,163,224,0.08)" : "transparent",
                borderRadius: 8, cursor: "pointer", marginBottom: 2,
                border: currentSessionId === s.id ? "1px solid rgba(0,163,224,0.2)" : "1px solid transparent",
                transition: "all 0.2s ease"
              }}
              onMouseOver={(e) => { if (currentSessionId !== s.id) e.currentTarget.style.background = "rgba(0,0,0,0.03)" }}
              onMouseOut={(e) => { if (currentSessionId !== s.id) e.currentTarget.style.background = "transparent" }}
              onClick={() => { if (editingSessionId !== s.id) loadSession(s.id) }}
            >
              {editingSessionId === s.id ? (
                <form
                  onSubmit={(e) => handleRenameSession(e, s.id)}
                  style={{ display: "flex", gap: "6px", width: "100%", alignItems: "center" }}
                >
                  <input
                    autoFocus
                    value={editSessionTitle}
                    onChange={(e) => setEditSessionTitle(e.target.value)}
                    style={{ flex: 1, background: "#fff", border: "1px solid #00A3E0", borderRadius: 4, padding: "4px 8px", fontSize: 13, outline: "none", boxShadow: "0 0 0 2px rgba(0, 163, 224, 0.2)" }}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button type="submit" style={{ background: "#10B981", border: "none", borderRadius: "4px", padding: "4px", color: "#fff", cursor: "pointer", display: "flex", alignItems: "center" }} onClick={(e) => e.stopPropagation()} title="Save">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  </button>
                  <button type="button" style={{ background: "#EF4444", border: "none", borderRadius: "4px", padding: "4px", color: "#fff", cursor: "pointer", display: "flex", alignItems: "center" }} onClick={(e) => { e.stopPropagation(); setEditingSessionId(null); }} title="Cancel">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  </button>
                </form>
              ) : (
                <>
                  <button
                    style={{
                      flex: 1, textAlign: "left", background: "none", border: "none", cursor: "pointer",
                      color: currentSessionId === s.id ? "#00A3E0" : "#374151",
                      fontWeight: currentSessionId === s.id ? 600 : 500,
                      fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                    }}
                  >
                    {s.title || "New Chat"}
                  </button>
                  <div style={{ display: "flex", gap: 2 }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditSessionTitle(s.title);
                        setEditingSessionId(s.id);
                      }}
                      style={{ background: "transparent", border: "none", cursor: "pointer", color: "#9CA3AF", padding: "6px", borderRadius: "6px", display: "flex", alignItems: "center", transition: "all 0.2s" }}
                      onMouseOver={(e) => { e.currentTarget.style.color = "#00A3E0"; e.currentTarget.style.background = "rgba(0,163,224,0.1)" }}
                      onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent" }}
                      title="Rename"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                    </button>
                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      style={{ background: "transparent", border: "none", cursor: "pointer", color: "#9CA3AF", padding: "6px", borderRadius: "6px", display: "flex", alignItems: "center", transition: "all 0.2s" }}
                      onMouseOver={(e) => { e.currentTarget.style.color = "#EF4444"; e.currentTarget.style.background = "rgba(239,68,68,0.1)" }}
                      onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent" }}
                      title="Delete"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
          {sessions.length === 0 && <div style={{ padding: "16px", textAlign: "center", color: "#9CA3AF", fontSize: 13 }}>No recent chats.</div>}
        </div>
      </div>

      {/* ── Main Chat Area ── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "var(--bg-main)",
        overflow: "hidden",
      }}>

        {/* ── Header ── */}
        <header style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "14px 24px",
          background: "#FFFFFF",
          borderBottom: "1px solid rgba(0,0,0,0.08)",
          boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
          flexShrink: 0,
          zIndex: 10,
        }}>
          {!isSidebarOpen && (
            <button onClick={() => setIsSidebarOpen(true)} title="Show Sidebar" style={{ background: "none", border: "none", cursor: "pointer", marginRight: 8, color: "#4B5563" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
          )}
          <DEHLogo size={40} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#111827", letterSpacing: "-0.01em" }}>
              AI Billing Agent
            </div>
            <div style={{ fontSize: 11, color: "#6B7280", marginTop: 1 }}>
              Powered by Hack to the Future
            </div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
            <button
              onClick={handleRestart}
              title="New Chat"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "#00A3E0",
                border: "none",
                borderRadius: 20,
                padding: "8px 16px",
                fontSize: 12,
                fontWeight: 600,
                color: "#FFFFFF",
                cursor: "pointer",
                boxShadow: "0 2px 6px rgba(0,163,224,0.3)",
                transition: "background 0.2s",
              }}
              onMouseOver={(e) => (e.currentTarget.style.background = "#008CBE")}
              onMouseOut={(e) => (e.currentTarget.style.background = "#00A3E0")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              New Chat
            </button>

          </div>
        </header>

        {/* ── Messages / Empty state ── */}
        <main style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          maxWidth: 720,
          width: "100%",
          margin: "0 auto",
        }}>
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            messages.map((msg) => (
              <Bubble key={msg.id} msg={msg} />
            ))
          )}
          <div ref={bottomRef} />
        </main>

        {/* ── Input area ── */}
        <div style={{
          flexShrink: 0,
          padding: "12px 16px 20px",
          background: "var(--bg-main)",
          position: "relative",
          zIndex: 10,
        }}>
          {/* Wrapper for Glow + Input */}
          <div style={{ position: "relative", maxWidth: 720, margin: "0 auto" }}>

            {/* Ambient Background Glow */}
            <div style={{
              position: "absolute",
              inset: -14,
              background: "linear-gradient(135deg, rgba(0,163,224,0.55) 0%, rgba(250,70,22,0.45) 100%)",
              filter: "blur(28px)",
              borderRadius: 32,
              opacity: isDragging ? 0.9 : 0.7,
              transition: "opacity 0.3s ease",
              pointerEvents: "none",
              zIndex: 0,
            }} />

            {/* Actual Input Container */}
            <div
              style={{
                position: "relative",
                zIndex: 1,
                width: "100%",
                background: isDragging ? "rgba(0,163,224,0.05)" : "rgba(255,255,255,0.9)",
                backdropFilter: "blur(8px)",
                border: isDragging ? "1px solid rgba(0,163,224,0.4)" : "1px solid rgba(255,255,255,0.6)",
                boxShadow: "0 2px 10px rgba(0,0,0,0.02)",
                borderRadius: 16,
                transition: "border-color 0.2s, background 0.2s, box-shadow 0.2s",
                overflow: "hidden",
              }}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              {/* File upload bar */}
              {files.length > 0 && (
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 14px",
                  borderBottom: "1px solid rgba(0,0,0,0.07)",
                  fontSize: 12,
                  color: "#00A3E0",
                }}>
                  <span></span>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {files.length === 1 ? files[0].name : `${files.length} files selected`}
                  </span>
                  <button
                    onClick={() => { setFiles([]); setExtracted(null); setMatchResult(null); }}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "#9CA3AF", fontSize: 16, lineHeight: 1, padding: "0 2px" }}
                  >×</button>
                </div>
              )}

              {/* Drag hint */}
              {isDragging && (
                <div style={{ textAlign: "center", padding: "16px", color: "#00A3E0", fontSize: 13 }}>
                  Drop your file here…
                </div>
              )}

              {/* Textarea */}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDrop(e as unknown as React.DragEvent); }}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
                placeholder={extracted ? "Ask a question about your bill…" : "Ask a question or drop your bill here…"}
                rows={1}
                style={{
                  display: "block",
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  resize: "none",
                  padding: "12px 14px",
                  fontSize: 14,
                  color: "#111827",
                  lineHeight: 1.6,
                  fontFamily: "inherit",
                  overflowY: "auto",
                  maxHeight: 120,
                }}
              />

              {/* Toolbar */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "0 10px 10px",
              }}>
                {/* Attach */}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*,application/pdf"
                  multiple
                  style={{ display: "none" }}
                  onChange={(e) => { Array.from(e.target.files ?? []).forEach((f) => handleFileChosen(f)); }}
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  title="Upload bill"
                  className="plus-btn"
                  style={{
                    background: "none",
                    border: "1px solid rgba(0,0,0,0.1)",
                    borderRadius: "50%",
                    width: 34,
                    height: 34,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    transition: "border-color 0.2s, background 0.2s",
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    className="plus-icon"
                  >
                    <path
                      d="M7 1V13M1 7H13"
                      stroke="#6B7280"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />
                  </svg>
                </button>

                <div style={{ flex: 1 }} />

                {/* Send / Stop */}
                {isTyping ? (
                  <button
                    onClick={handleStop}
                    title="Stop generation"
                    style={{
                      background: "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)",
                      border: "none",
                      borderRadius: 10,
                      width: 36,
                      height: 36,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      transition: "background 0.25s",
                    }}
                    onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.93)"; }}
                    onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = ""; }}
                  >
                    <div style={{ width: 12, height: 12, background: "#FFFFFF", borderRadius: 2 }} />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={files.length === 0 && !input.trim()}
                    style={{
                      background: (input.trim() || files.length > 0)
                        ? "linear-gradient(135deg, #00A3E0 0%, #e8f7fd 100%)"
                        : "rgba(0,0,0,0.05)",
                      border: "none",
                      borderRadius: 10,
                      width: 36,
                      height: 36,
                      cursor: (input.trim() || files.length > 0) ? "pointer" : "not-allowed",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      transition: "background 0.25s",
                    }}
                    onMouseDown={(e) => { if (input.trim() || files.length > 0) (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.93)"; }}
                    onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = ""; }}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      className={input.trim() || files.length > 0 ? "arrow-up" : "arrow-right"}
                      style={{ display: "block" }}
                    >
                      <path
                        d="M3 8L13 8M13 8L8.5 3.5M13 8L8.5 12.5"
                        stroke={input.trim() ? "#0077a8" : "#9CA3AF"}
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>

          <div style={{ textAlign: "center", marginTop: 8, fontSize: 10, color: "#D1D5DB" }}>
            All Rights Reserved © Hack to the Future {new Date().getFullYear()}
          </div>
        </div>
      </div>
    </div>
  );
}
