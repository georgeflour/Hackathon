"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { uploadBill, matchBill, explainBill } from "@/lib/api";

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
          border: isUser ? "1px solid rgba(0,163,224,0.15)" : "1px solid rgba(0,0,0,0.08)",
          boxShadow: isUser ? "0 1px 6px rgba(0,163,224,0.1)" : "0 1px 4px rgba(0,0,0,0.06)",
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

  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  function addMsg(msg: Omit<Message, "id">) {
    const full: Message = { ...msg, id: uid() };
    setMessages((prev) => [...prev, full]);
    return full.id;
  }

  function updateMsg(id: string, patch: Partial<Message>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  /* ── attach file (no processing yet) ── */
  function handleFileChosen(chosen: File) {
    setFiles((prev) => [...prev, chosen]);
  }

  /* ── process all pending files through Agent 1 + 2 ── */
  async function processFiles(pending: File[]): Promise<{ ext: Record<string, unknown>; match: Record<string, unknown> } | null> {
    const typingId = addMsg({ role: "assistant", content: "…" });
    setIsTyping(true);

    try {
      const ext = await uploadBill(pending[0]);
      setExtracted(ext);
      updateMsg(typingId, {
        content: "I analyzed your bill. Here are the extracted details:",
        stage: "upload",
        payload: ext,
      });

      const match = await matchBill(ext);
      setMatchResult(match);
      const matchId = addMsg({ role: "assistant", content: "…" });
      updateMsg(matchId, {
        content: "Found your profile in the system:",
        stage: "match",
        payload: match,
      });

      setFiles([]);
      return { ext, match };
    } catch (e) {
      updateMsg(typingId, { content: `Error: ${String(e)}` });
      return null;
    } finally {
      setIsTyping(false);
    }
  }

  /* ── send: handles files + optional question ── */
  async function handleSend() {
    const q = input.trim();
    const hasPendingFiles = files.length > 0;
    const hasQuestion = q.length > 0;

    if (!hasPendingFiles && !hasQuestion) return;

    setInput("");
    setIsTyping(true);

    // Compose a single user bubble combining files + text
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));
    const nonImageFiles = files.filter((f) => !f.type.startsWith("image/"));
    const imageUrls = imageFiles.map((f) => URL.createObjectURL(f));
    const nonImageNames = nonImageFiles.length > 0 ? `📎 ${nonImageFiles.map((f) => f.name).join(", ")}` : "";
    const userContent = [nonImageNames, hasQuestion ? q : ""].filter(Boolean).join("\n");
    addMsg({ role: "user", content: userContent, imageUrls: imageUrls.length > 0 ? imageUrls : undefined });
    setFiles([]); // clear attachment bar immediately

    let currentExtracted = extracted;
    let currentMatch = matchResult;

    // Step 1: process pending files if any
    if (hasPendingFiles) {
      const result = await processFiles(files);
      if (!result) {
        // processFiles already showed the error bubble — stop here
        setIsTyping(false);
        return;
      }
      currentExtracted = result.ext;
      currentMatch = result.match;
      if (!hasQuestion) {
        addMsg({
          role: "assistant",
          content: "You can now ask me anything about your bill, e.g. \"Why is my bill higher than usual?\"",
        });
        setIsTyping(false);
        return;
      }
    }

    // Step 2: answer question if provided
    if (hasQuestion) {
      if (!currentExtracted || !currentMatch) {
        addMsg({
          role: "assistant",
          content: "Please upload your bill first so I can answer your question.",
        });
        setIsTyping(false);
        return;
      }

      const typingId = addMsg({ role: "assistant", content: "…" });

      try {
        const result = await explainBill(currentExtracted, currentMatch, q);
        const answerText =
          (result.answer_text as string) ||
          (result.answer as string) ||
          JSON.stringify(result);
        updateMsg(typingId, { content: answerText });
      } catch (e) {
        updateMsg(typingId, { content: `Error: ${String(e)}` });
      } finally {
        setIsTyping(false);
      }
    }
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
    <div style={{
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
        <DEHLogo size={40} />
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#111827", letterSpacing: "-0.01em" }}>
            AI Billing Agent
          </div>
          <div style={{ fontSize: 11, color: "#6B7280", marginTop: 1 }}>
            Powered by Hack to the Future
          </div>
        </div>
        <div style={{
          marginLeft: "auto",
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 11,
          fontWeight: 600,
          color: "#FFFFFF",
          background: "linear-gradient(135deg, #FA4616 0%, #00A3E0 100%)",
          border: "none",
          borderRadius: 20,
          padding: "4px 12px",
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(255,255,255,0.85)", display: "inline-block" }} />
          Online
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
        borderTop: "1px solid rgba(0,0,0,0.07)",
      }}>
        <div
          style={{
            maxWidth: 720,
            margin: "0 auto",
            background: isDragging ? "rgba(0,163,224,0.05)" : "#FFFFFF",
            border: `1px solid ${isDragging ? "rgba(0,163,224,0.4)" : "rgba(0,0,0,0.1)"}`,
            boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
            borderRadius: 16,
            transition: "border-color 0.2s, background 0.2s",
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

            {/* Send */}
            <button
              onClick={handleSend}
              disabled={(files.length === 0 && !input.trim()) || isTyping}
              style={{
                background: (input.trim() || files.length > 0) && !isTyping
                  ? "linear-gradient(135deg, #00A3E0 0%, #e8f7fd 100%)"
                  : "rgba(0,0,0,0.05)",
                border: "none",
                borderRadius: 10,
                width: 36,
                height: 36,
                cursor: (input.trim() || files.length > 0) && !isTyping ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "background 0.25s",
              }}
              onMouseDown={(e) => { if ((input.trim() || files.length > 0) && !isTyping) (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.93)"; }}
              onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = ""; }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className={(input.trim() || files.length > 0) && !isTyping ? "arrow-up" : "arrow-right"}
                style={{ display: "block" }}
              >
                <path
                  d="M3 8L13 8M13 8L8.5 3.5M13 8L8.5 12.5"
                  stroke={input.trim() && !isTyping ? "#0077a8" : "#9CA3AF"}
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>

        <div style={{ textAlign: "center", marginTop: 8, fontSize: 10, color: "#D1D5DB" }}>
          All Rights Reserved © Hack to the Future {new Date().getFullYear()}
        </div>
      </div>
    </div>
  );
}
