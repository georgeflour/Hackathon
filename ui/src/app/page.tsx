"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { uploadBill } from "@/lib/api";

/* ─── types ──────────────────────────────────────────────────────────── */
type Role = "user" | "assistant" | "system";
interface Message {
  id: string;
  role: Role;
  content: string;
  imageUrls?: string[];          // blob preview URLs for image attachments
  stage?: "upload" | "match" | "answer";
  payload?: Record<string, unknown>;
  attachments?: File[];
  verification?: "pending" | "approved" | "rejected" | "editing";
  pendingQuestion?: string;
  typingType?: "upload" | "chat";
}

/* ─── helpers ────────────────────────────────────────────────────────── */
function uid() {
  return Math.random().toString(36).slice(2);
}

function DEHLogo({ size = 38 }: { size?: number }) {
  return (
    <Image
      src="/woman-picture.png"
      alt="ΔΕΗ Logo"
      width={size}
      height={size}
      style={{ borderRadius: 8, objectFit: "cover" }}
      priority
    />
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good Morning!";
  if (hour >= 12 && hour < 17) return "Good Afternoon!";
  if (hour >= 17 && hour < 21) return "Good Evening!";
  return "Hello Night Owl!";
}

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
      userSelect: "none",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 48,
        height: 48,
        borderRadius: "50%",
        background: "rgba(0,163,224,0.05)",
        color: "#00A3E0",
        marginBottom: 8,
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
      </div>
      <div style={{
        fontSize: 28,
        fontWeight: 400,
        color: "#374151",
        letterSpacing: "-0.02em",
        lineHeight: 1.1,
        textAlign: "center",
      }}>
        {getGreeting()}
      </div>
      <div style={{
        fontSize: 14,
        color: "#9CA3AF",
        fontWeight: 400,
        textAlign: "center",
        letterSpacing: "0.01em",
      }}>
        How can I help you today?
      </div>
    </div>
  );
}

function TypingDots({ type }: { type?: "upload" | "chat" }) {
  const [msgIdx, setMsgIdx] = useState(0);

  const msgs = type === "upload"
    ? ["Εξαγωγή δεδομένων...", "Ανάλυση εικόνας...", "Αναγνώριση πεδίων..."]
    : ["Σύνδεση με τον AI Agent...", "Αναζήτηση στη βάση γνώσης...", "Αξιολόγηση πληροφοριών...", "Σύνταξη απάντησης..."];

  useEffect(() => {
    if (!type) return;
    const interval = setInterval(() => {
      setMsgIdx((prev) => (prev + 1) % msgs.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [type, msgs.length]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: "2px 0" }}>
      {type && (
        <span className="fade-up" key={msgIdx} style={{
          fontSize: 12, color: "#9CA3AF", fontStyle: "italic"
        }}>
          {msgs[msgIdx]}
        </span>
      )}
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px" }}>
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </span>
    </div>
  );
}

function MetricsBadges({ metrics }: { metrics: any }) {
  const [hovered, setHovered] = useState<string | null>(null);

  // Fallback defaults in case backend is outdated
  if (!metrics) return null;

  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
      {/* Confidence */}
      <div
        style={{ position: "relative" }}
        onMouseEnter={() => setHovered("confidence")}
        onMouseLeave={() => setHovered(null)}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          padding: "4px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
          background: "rgba(0,163,224,0.06)", border: "1px solid rgba(0,163,224,0.15)",
          color: "#00A3E0", cursor: "help", transition: "all 0.2s"
        }}>
          🎯 Confidence: {metrics.confidence}%
        </span>
        {hovered === "confidence" && (
          <div className="fade-up" style={{
            position: "absolute", top: "100%", left: 0, marginTop: 4, width: 220, zIndex: 50,
            background: "#fff", border: "1px solid #E5E7EB", borderRadius: 8, padding: 10,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 12, color: "#374151",
            lineHeight: 1.4
          }}>
            <strong style={{ display: "block", marginBottom: 4, color: "#111827" }}>Scientific Calibration</strong>
            {metrics.formulas && metrics.formulas.confidence && (
              <div style={{ padding: 4, background: "#F9FAFB", borderRadius: 4, fontFamily: "monospace", fontSize: 10, marginBottom: 6 }}>{metrics.formulas.confidence}</div>
            )}
            <div style={{ fontSize: 11, color: "#6B7280" }}>Calculated post-hoc based on chunk similarity, support count, and source agreement.</div>
          </div>
        )}
      </div>

      {/* Hallucination Risk */}
      <div
        style={{ position: "relative" }}
        onMouseEnter={() => setHovered("hallucination")}
        onMouseLeave={() => setHovered(null)}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          padding: "4px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
          background: "rgba(245, 158, 11, 0.06)", border: "1px solid rgba(245, 158, 11, 0.15)",
          color: "#D97706", cursor: "help", transition: "all 0.2s"
        }}>
          🛡️ Hallucination Risk: {metrics.hallucinationRisk}
        </span>
        {hovered === "hallucination" && (
          <div className="fade-up" style={{
            position: "absolute", top: "100%", left: 0, marginTop: 4, width: 220, zIndex: 50,
            background: "#fff", border: "1px solid #E5E7EB", borderRadius: 8, padding: 10,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 12, color: "#374151",
            lineHeight: 1.4
          }}>
            <strong style={{ display: "block", marginBottom: 4, color: "#111827" }}>Claim Verification</strong>
            {metrics.formulas && metrics.formulas.hallucinationRisk && (
              <div style={{ padding: 4, background: "#F9FAFB", borderRadius: 4, fontFamily: "monospace", fontSize: 10, marginBottom: 6 }}>{metrics.formulas.hallucinationRisk}</div>
            )}
            <div style={{ fontSize: 11, color: "#6B7280" }}>Measures unsupported vs supported claims derived directly from context docs.</div>
          </div>
        )}
      </div>

      {/* Explainability */}
      <div
        style={{ position: "relative" }}
        onMouseEnter={() => setHovered("explainability")}
        onMouseLeave={() => setHovered(null)}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          padding: "4px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
          background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.15)",
          color: "#059669", cursor: "help", transition: "all 0.2s"
        }}>
          🔍 Explainability Trace
        </span>
        {hovered === "explainability" && (
          <div className="fade-up" style={{
            position: "absolute", top: "100%", right: 0, marginTop: 4, width: 280, zIndex: 50,
            background: "#fff", border: "1px solid #E5E7EB", borderRadius: 8, padding: 10,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 12, color: "#374151",
            lineHeight: 1.4
          }}>
            <strong style={{ display: "block", marginBottom: 6, color: "#111827" }}>Claim-to-Evidence Mapping</strong>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {metrics.explainability && metrics.explainability.map((item: any, i: number) => (
                <div key={i} style={{ padding: 6, background: "#F3F4F6", borderRadius: 6 }}>
                  <div style={{ fontStyle: "italic", marginBottom: 4, fontSize: 11, color: "#111827" }}>"{item.claim}"</div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 10, color: "#6B7280", background: "#E5E7EB", padding: "2px 6px", borderRadius: 4 }}>{item.source}</span>
                    <span style={{ fontSize: 10, color: item.supported ? "#059669" : "#D97706", fontWeight: 700, textTransform: "uppercase" }}>{item.support}</span>
                  </div>
                </div>
              ))}
              {(!metrics.explainability || metrics.explainability.length === 0) && (
                <span style={{ fontSize: 11, color: "#9CA3AF" }}>No specific claims detected.</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── card for extracted / match data ───────────────────────────────── */
function DataCard({ title, data, onEdit }: { title: string; data: Record<string, unknown>; onEdit?: (k: string, v: string) => void }) {
  const labelMap: Record<string, string> = {
    account_number: "Α/Α ΛΟΓΑΡΙΑΣΜΟΥ",
    supply_number: "ΑΡΙΘΜΟΣ ΠΑΡΟΧΗΣ",
    customer_address: "ΔΙΕΥΘΥΝΣΗ ΑΚΙΝΗΤΟΥ",
    vendor_name: "ΕΚΔΟΤΗΣ",
    bill_type: "ΤΥΠΟΣ ΛΟΓΑΡΙΑΣΜΟΥ",
    tariff_status: "ΚΑΤΑΣΤΑΣΗ ΤΙΜΟΛΟΓΙΟΥ",
    tariff_type: "ΤΙΜΟΛΟΓΙΟ",
    invoice_due_date: "ΕΞΟΦΛΗΣΗ ΕΩΣ",
    next_meter_read_date: "ΕΠΟΜΕΝΗ ΚΑΤΑΜΕΤΡΗΣΗ",
    issue_date: "ΗΜ/ΝΙΑ ΕΚΔΟΣΗΣ",
    service_period_start: "ΠΕΡΙΟΔΟΣ ΑΠΟ",
    service_period_end: "ΠΕΡΙΟΔΟΣ ΕΩΣ",
    kwh_consumed: "ΚΑΤΑΝΑΛΩΣΗ (kWh)",
    invoice_total_eur: "ΠΟΣΟ ΠΛΗΡΩΜΗΣ",
    billing_days: "ΗΜΕΡΕΣ ΚΑΤΑΝΑΛΩΣΗΣ",
    payment_reference: "ΚΩΔΙΚΟΣ ΠΛΗΡΩΜΗΣ (RF)",
  };

  const fieldOrder = [
    "account_number",
    "supply_number",
    "customer_address",
    "vendor_name",
    "bill_type",
    "tariff_status",
    "tariff_type",
    "invoice_due_date",
    "issue_date",
    "invoice_total_eur",
    "kwh_consumed",
  ];

  const rows = Object.entries(data)
    .filter(([k, v]) => v !== null && v !== undefined && v !== "" && !k.startsWith("source_file") && k !== "metrics" && k !== "explainability")
    .sort((a, b) => {
      const idxA = fieldOrder.indexOf(a[0]);
      const idxB = fieldOrder.indexOf(b[0]);
      if (idxA === -1 && idxB === -1) return 0;
      if (idxA === -1) return 1;
      if (idxB === -1) return -1;
      return idxA - idxB;
    });

  const getLabel = (k: string) => labelMap[k] || k.replace(/_/g, " ").toUpperCase();

  if (onEdit) {
    return (
      <div className="fade-up" style={{
        background: "linear-gradient(135deg, rgba(0,163,224,0.06) 0%, rgba(0,163,224,0.12) 100%)",
        border: "1px solid rgba(0,163,224,0.4)",
        boxShadow: "0 8px 24px rgba(0,163,224,0.12)",
        borderRadius: 12,
        padding: "16px 20px",
        marginTop: 10,
      }}>
        <div style={{ color: "#00A3E0", fontWeight: 700, marginBottom: 16, fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00A3E0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
          ΔΙΟΡΘΩΣΗ ΣΤΟΙΧΕΙΩΝ
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {rows.slice(0, 15).map(([k, v]) => {
            const isEditable = k === "account_number" || k === "supply_number";
            return (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "140px 1fr", alignItems: "center", gap: 8 }}>
                <label style={{ fontSize: 10, color: "#4B5563", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.02em", textAlign: "right", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={getLabel(k)}>{getLabel(k)}</label>
                <input
                  value={String(v)}
                  readOnly={!isEditable}
                  onChange={isEditable ? (e) => onEdit(k, e.target.value) : undefined}
                  style={{
                    padding: "6px 10px", borderRadius: 6,
                    border: isEditable ? "1px solid rgba(0,163,224,0.3)" : "1px solid transparent",
                    fontSize: 13, color: isEditable ? "#004763" : "#6B7280", outline: "none", width: "100%",
                    boxSizing: "border-box", transition: "all 0.2s",
                    background: isEditable ? "rgba(255,255,255,0.7)" : "transparent",
                    fontWeight: 500,
                    cursor: isEditable ? "text" : "default"
                  }}
                  onFocus={isEditable ? (e) => { e.currentTarget.style.borderColor = "#00A3E0"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(0,163,224,0.2)"; e.currentTarget.style.background = "#fff"; } : undefined}
                  onBlur={isEditable ? (e) => { e.currentTarget.style.borderColor = "rgba(0,163,224,0.3)"; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.background = "rgba(255,255,255,0.7)"; } : undefined}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  }

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
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 14px", alignItems: "baseline" }}>
        {rows.slice(0, 15).map(([k, v]) => (
          <div key={k} style={{ display: "contents" }}>
            <span style={{ color: "#9CA3AF", whiteSpace: "nowrap", fontSize: 11, fontWeight: 500 }}>{getLabel(k)}</span>
            <span style={{ color: "#111827", wordBreak: "break-all", fontWeight: 500 }}>{String(v)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


/* ─── individual chat bubble ─────────────────────────────────────────── */
function Bubble({ msg, onVerify, onCancelEdit, onEditPayload }: { msg: Message, onVerify?: (id: string, ok: boolean) => void, onCancelEdit?: (id: string) => void, onEditPayload?: (id: string, newPayload: Record<string, unknown>) => void }) {
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
          overflow: "visible",
        }}>
          {!isUser && msg.payload && (msg.payload as any).metrics && (
            <MetricsBadges metrics={(msg.payload as any).metrics} />
          )}
          {!isUser && msg.payload && (msg.payload as any).metrics?.thoughtTime && msg.content !== "…" && (
            <div style={{ fontSize: 12, color: "#6B7280", marginBottom: 8, display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "rgba(0,0,0,0.04)", borderRadius: 6, width: "fit-content" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
              Thought for {(msg.payload as any).metrics.thoughtTime} s
            </div>
          )}
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
          {msg.content && (msg.content === "…" ? <TypingDots type={msg.typingType} /> : <span style={{ padding: msg.imageUrls?.length ? "0 6px 4px" : undefined, display: "block" }}>{msg.content}</span>)}
        </div>

        {/* Optional structured payload */}
        {msg.payload && msg.stage === "upload" && (
          <>
            <DataCard
              title={msg.verification === "editing" ? "Επεξεργασία Στοιχείων Λογαριασμού" : "Bill Extracted"}
              data={msg.payload as Record<string, unknown>}
              onEdit={msg.verification === "editing" ? (k, v) => onEditPayload?.(msg.id, { ...msg.payload, [k]: v } as Record<string, unknown>) : undefined}
            />

            {msg.verification === "editing" && (
              <div className="fade-up" style={{ marginTop: 16, display: "flex", gap: 10, alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap" }}>
                <button
                  onClick={() => onCancelEdit?.(msg.id)}
                  style={{
                    padding: "8px 16px", borderRadius: "8px", background: "#FFFFFF", color: "#6B7280",
                    border: "1px solid #D1D5DB", cursor: "pointer", fontSize: 13, fontWeight: 600, transition: "all 0.2s"
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.background = "#F3F4F6"; e.currentTarget.style.color = "#374151"; }}
                  onMouseOut={(e) => { e.currentTarget.style.background = "#FFFFFF"; e.currentTarget.style.color = "#6B7280"; }}
                >
                  Ακύρωση
                </button>
                <button
                  onClick={() => onVerify?.(msg.id, true)}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "8px 20px", borderRadius: "8px", background: "#00A3E0", color: "#fff",
                    border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, transition: "all 0.2s",
                    boxShadow: "0 2px 6px rgba(0,163,224,0.3)"
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.background = "#008CBE"; e.currentTarget.style.boxShadow = "0 4px 10px rgba(0,163,224,0.4)"; }}
                  onMouseOut={(e) => { e.currentTarget.style.background = "#00A3E0"; e.currentTarget.style.boxShadow = "0 2px 6px rgba(0,163,224,0.3)"; }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  Αποθήκευση
                </button>
              </div>
            )}

            {msg.verification === "pending" && (
              <div className="fade-up" style={{
                marginTop: 12, display: "flex", gap: 8, alignItems: "center",
                padding: "10px 14px", background: "rgba(0,163,224,0.05)",
                border: "1px solid rgba(0,163,224,0.2)", borderRadius: 12
              }}>
                <span style={{ fontSize: 13, color: "#374151", fontWeight: 500, flex: 1 }}>Είναι αυτά τα στοιχεία σωστά;</span>
                <button
                  onClick={() => onVerify?.(msg.id, true)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", padding: "6px",
                    borderRadius: "6px", background: "transparent", color: "#10B981", border: "none", cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.background = "rgba(16, 185, 129, 0.1)"; }}
                  onMouseOut={(e) => { e.currentTarget.style.background = "transparent"; }}
                  title="Επιβεβαίωση"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </button>
                <button
                  onClick={() => onVerify?.(msg.id, false)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", padding: "6px",
                    borderRadius: "6px", background: "transparent", color: "#EF4444", border: "none", cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)"; }}
                  onMouseOut={(e) => { e.currentTarget.style.background = "transparent"; }}
                  title="Απόρριψη και Διόρθωση"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>
            )}
            {msg.verification === "approved" && (
              <div className="fade-up" style={{ marginTop: 8, fontSize: 12, color: "#10B981", display: "flex", alignItems: "center", gap: 4 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                Επιβεβαιώθηκαν
              </div>
            )}
            {msg.verification === "rejected" && (
              <div className="fade-up" style={{ marginTop: 8, fontSize: 12, color: "#EF4444", display: "flex", alignItems: "center", gap: 4 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                Απορρίφθηκαν
              </div>
            )}
          </>
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
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [isResizing, setIsResizing] = useState(false);

  // History Edit State
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editSessionTitle, setEditSessionTitle] = useState("");

  // Voice Recording State
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const originalInputRef = useRef<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "el-GR";

        recognition.onresult = (event: any) => {
          const transcript = Array.from(event.results)
            .map((res: any) => res[0].transcript)
            .join('');

          const prefix = originalInputRef.current ? originalInputRef.current + " " : "";
          setInput(prefix + transcript);
        };

        recognition.onerror = () => setIsListening(false);
        recognition.onend = () => setIsListening(false);
        recognitionRef.current = recognition;
      }
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      originalInputRef.current = input;
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch (e) {
        console.error(e);
      }
    }
  };


  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      let newWidth = e.clientX;
      if (newWidth < 200) newWidth = 200; // min width
      if (newWidth > 600) newWidth = 600; // max width
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = "auto";
    };
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "none"; // prevent text selection while dragging
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "auto";
    };
  }, [isResizing]);

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
    localStorage.removeItem("deh_account_number");
    localStorage.removeItem("deh_supply_number");
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

  async function handleVerify(msgId: string, ok: boolean) {
    const msg = messages.find(m => m.id === msgId);
    if (!msg) return;

    if (ok) {
      updateMsg(msgId, { verification: "approved" });
      setExtracted(msg.payload as Record<string, unknown>);
    } else {
      updateMsg(msgId, { verification: "editing" });
      return;
    }

    if (msg.pendingQuestion) {
      const q = msg.pendingQuestion;
      abortControllerRef.current = new AbortController();
      const typingId = addMsg({ role: "assistant", content: "…", typingType: "chat" });
      setIsTyping(true);
      try {
        const { chatWithAssistant } = await import("@/lib/api");
        const ragContent = msg.payload ? `Bill Extracted Data:\n${JSON.stringify(msg.payload, null, 2)}` : "";
        const explanation = await chatWithAssistant(q, ragContent, "", { signal: abortControllerRef.current.signal });
        const textAnswer = (explanation?.answer as string) || (explanation?.message as string) || "Done.";
        updateMsg(typingId, {
          content: textAnswer,
          stage: "answer",
          payload: explanation
        });

        if (currentSessionId) {
          import("@/lib/api").then(api => api.saveMessage(currentSessionId, "assistant", textAnswer)).catch(console.error);
        }
      } catch (e: any) {
        if (e.name === "AbortError") {
          removeMsg(typingId);
        } else {
          updateMsg(typingId, { content: `Assistant is not fully wired up for questions yet, but I received: "${q}"\n\n(Error: ${String(e)})` });
        }
      }
      setIsTyping(false);
    } else {
      addMsg({
        role: "assistant",
        content: "Τα δεδομένα επιβεβαιώθηκαν! Μπορείτε πλέον να με ρωτήσετε οτιδήποτε σχετικό με τον λογαριασμό σας.",
      });
    }
  }

  function addMsg(msg: Omit<Message, "id">) {
    const full: Message = { ...msg, id: uid() };
    setMessages((prev) => [...prev, full]);
    return full.id;
  }

  function handleCancelEdit(id: string) {
    updateMsg(id, { verification: "rejected" });
    addMsg({
      role: "assistant",
      content: "Η διαδικασία εισαγωγής ακυρώθηκε. Παρακαλώ ανεβάστε ξανά μια πιο καθαρή φωτογραφία του λογαριασμού σας.",
    });
    setExtracted(null);
    setFiles([]);
  }

  function updateMsg(id: string, patch: Partial<Message>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  function handleEditPayload(id: string, newPayload: Record<string, unknown>) {
    updateMsg(id, { payload: newPayload });
  }

  function removeMsg(id: string) {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }

  /* ── attach file (no processing yet) ── */
  function handleFileChosen(chosen: File) {
    setFiles((prev) => [...prev, chosen]);
  }

  /* ── process files: upload only ── */
  async function processFiles(pending: File[], pendingQuestion?: string): Promise<Record<string, unknown> | null> {
    const typingId = addMsg({ role: "assistant", content: "…", typingType: "upload" });
    setIsTyping(true);

    abortControllerRef.current = new AbortController();

    try {
      const ext = await uploadBill(pending, { signal: abortControllerRef.current.signal });
      setExtracted(ext);

      // ── Persist identifiers so they survive page reloads ──────────
      const accountNum = (ext?.account_number as string) ?? "";
      const supplyNum  = (ext?.supply_number  as string) ?? "";
      if (accountNum) localStorage.setItem("deh_account_number", accountNum);
      if (supplyNum)  localStorage.setItem("deh_supply_number",  supplyNum);
      console.log("[processFiles] 💾 persisted to localStorage → account_number:", accountNum, "| supply_number:", supplyNum);

      updateMsg(typingId, {
        content: "I analysed your bill. Are these extracted details correct?",
        stage: "upload",
        payload: ext,
        verification: "pending",
        pendingQuestion: pendingQuestion,
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

    // ── Recover extracted payload if state was lost ───────────────
    if (!currentExtracted) {
      // 1. Try in-memory messages (same session, no reload)
      const lastUpload = [...messages].reverse().find(m => m.stage === "upload" && m.payload);
      if (lastUpload?.payload) {
        currentExtracted = lastUpload.payload as Record<string, unknown>;
        setExtracted(currentExtracted);
        console.log("[handleSend] ♻️  recovered extracted from upload message payload");
      } else {
        // 2. Fall back to localStorage (survives page reloads)
        const storedAccount = localStorage.getItem("deh_account_number");
        const storedSupply  = localStorage.getItem("deh_supply_number");
        if (storedAccount || storedSupply) {
          currentExtracted = { account_number: storedAccount ?? "", supply_number: storedSupply ?? "" };
          console.log("[handleSend] ♻️  recovered identifiers from localStorage → account_number:", storedAccount, "| supply_number:", storedSupply);
        }
      }
    }

    console.log("[handleSend] ── START ──────────────────────────────");
    console.log("[handleSend] question:", q || "(none)");
    console.log("[handleSend] files attached:", pendingFiles.length);
    console.log("[handleSend] currentSessionId:", localSessionId);
    console.log("[handleSend] extracted state on entry:", currentExtracted);

    // 1. Recover files if we have no files, no extracted data, but a previous upload was aborted.
    if (pendingFiles.length === 0 && !currentExtracted) {
      const lastUserMsg = messages.slice().reverse().find(m => m.role === "user");
      if (lastUserMsg?.attachments?.length) {
        pendingFiles = lastUserMsg.attachments;
        console.log("[handleSend] recovered", pendingFiles.length, "file(s) from previous message");
      }
    }

    if (pendingFiles.length === 0 && !hasQuestion) {
      console.log("[handleSend] nothing to send — aborting");
      return;
    }

    setInput("");
    setIsTyping(true);

    // 2. Add user message
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));
    const nonImageFiles = files.filter((f) => !f.type.startsWith("image/"));
    const imageUrls = imageFiles.map((f) => URL.createObjectURL(f));
    const nonImageNames = nonImageFiles.length > 0 ? `📎 ${nonImageFiles.map((f) => f.name).join(", ")}` : "";
    const userContent = [nonImageNames, hasQuestion ? q : ""].filter(Boolean).join("\n");

    console.log("[handleSend] userContent:", userContent);
    console.log("[handleSend] imageFiles:", imageFiles.length, "| nonImageFiles:", nonImageFiles.length);

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
        console.log("[handleSend] new session created:", localSessionId);
        api.getSessions().then((data) => setSessions(data as any)).catch(console.error);
      } else {
        console.log("[handleSend] reusing existing session:", localSessionId);
      }
      await api.saveMessage(localSessionId, "user", userContent, imageBase64s);
      console.log("[handleSend] user message saved to history");
    } catch (e) { console.error("[handleSend] session/save error:", e); }

    setFiles([]);

    // 3. Process Files (Upload + Extract) if needed
    const isExplicitUpload = files.length > 0;
    console.log("[handleSend] isExplicitUpload:", isExplicitUpload, "| has currentExtracted:", !!currentExtracted);
    if (isExplicitUpload || (pendingFiles.length > 0 && !currentExtracted)) {
      console.log("[handleSend] ── uploading & extracting bill ──────");
      const ext = await processFiles(pendingFiles, hasQuestion ? q : undefined);
      if (!ext) {
        console.warn("[handleSend] extraction returned null — stopping");
        setIsTyping(false);
        return;
      }
      currentExtracted = ext;
      console.log("[handleSend] extraction result:", currentExtracted);
      setIsTyping(false);
      return; // Stop here and wait for the user to click Tick or Cross
    }

    // 4. Handle Questions
    if (hasQuestion) {
      abortControllerRef.current = new AbortController();
      const typingId = addMsg({ role: "assistant", content: "…", typingType: "chat" });
      setIsTyping(true);
      try {
        const { chatWithAssistant } = await import("@/lib/api");

        // Extract identifiers for SQLite lookup
        // account_number → Bills.AccountNumber  (primary,  e.g. "20260318003")
        // supply_number  → Bills.Arxikos_Paroxis (fallback, e.g. "650182947331")
        // Priority: currentExtracted (from OCR) → localStorage (persisted from last upload)
        const accountNumber =
          (currentExtracted?.account_number as string) ||
          localStorage.getItem("deh_account_number") ||
          "";
        const supplyNumber =
          (currentExtracted?.supply_number as string) ||
          localStorage.getItem("deh_supply_number") ||
          "";

        console.log("[handleSend] ── calling chatWithAssistant ────────");
        console.log("[handleSend] question sent to API:", q);
        console.log("[handleSend] accountNumber (primary):", accountNumber || "(empty)");
        console.log("[handleSend] supplyNumber  (fallback):", supplyNumber || "(empty)");
        console.log("[handleSend] source → extracted:", !!currentExtracted?.account_number, "| localStorage:", !!localStorage.getItem("deh_account_number"));
        console.log("[handleSend] DB lookup will fire:", !!(accountNumber || supplyNumber));

        const explanation = await chatWithAssistant(q, "", "", supplyNumber, accountNumber, { signal: abortControllerRef.current.signal });

        console.log("[handleSend] ── response received ─────────────────");
        console.log("[handleSend] raw API response:", explanation);

        const ragContent = currentExtracted ? `Bill Extracted Data:\n${JSON.stringify(currentExtracted, null, 2)}` : "";
        const explanation = await chatWithAssistant(q, ragContent, "", { signal: abortControllerRef.current.signal });
        const textAnswer = (explanation?.answer as string) || (explanation?.message as string) || "Done.";
        console.log("[handleSend] textAnswer:", textAnswer?.slice(0, 120), textAnswer?.length > 120 ? "…" : "");

        updateMsg(typingId, {
          content: textAnswer,
          stage: "answer",
          payload: explanation
        });

        if (localSessionId) {
          import("@/lib/api").then(api => api.saveMessage(localSessionId as string, "assistant", textAnswer)).catch(console.error);
          console.log("[handleSend] assistant message saved to history");
        }
      } catch (e: any) {
        if (e.name === "AbortError") {
          console.log("[handleSend] request aborted by user");
          removeMsg(typingId);
        } else {
          console.error("[handleSend] chatWithAssistant error:", e);
          updateMsg(typingId, { content: `Assistant is not fully wired up for questions yet, but I received: "${q}"\n\n(Error: ${String(e)})` });
        }
      }
    } else if (pendingFiles.length > 0) {
      console.log("[handleSend] files uploaded but no question — prompting user");
      addMsg({
        role: "assistant",
        content: "You can now ask me anything about your bill, e.g. \"Why is my bill higher than usual?\"",
      });
    }

    console.log("[handleSend] ── END ────────────────────────────────");
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
        width: sidebarWidth,
        flexShrink: 0,
        background: "#FFFFFF",
        borderRight: "1px solid rgba(0,0,0,0.08)",
        display: isSidebarOpen ? "flex" : "none",
        flexDirection: "column",
        position: "relative",
        zIndex: 20,
      }}>
        {/* Resizer handle */}
        <div
          onMouseDown={() => setIsResizing(true)}
          style={{
            position: "absolute",
            top: 0,
            right: -3,
            width: 6,
            height: "100%",
            cursor: "col-resize",
            zIndex: 30,
            background: isResizing ? "rgba(0,163,224,0.5)" : "transparent",
            transition: "background 0.2s",
          }}
          onMouseOver={(e) => { e.currentTarget.style.background = "rgba(0,163,224,0.3)"; }}
          onMouseOut={(e) => { e.currentTarget.style.background = isResizing ? "rgba(0,163,224,0.5)" : "transparent"; }}
        />
        <div style={{ padding: "16px", borderBottom: "1px solid rgba(0,0,0,0.08)", fontWeight: 600, color: "#111827", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            Chat History
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "2px" }}>
            <button
              onClick={handleRestart}
              style={{
                background: "transparent", border: "none", cursor: "pointer", color: "#9CA3AF",
                padding: "6px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.2s"
              }}
              onMouseOver={(e) => { e.currentTarget.style.color = "#00A3E0"; e.currentTarget.style.background = "rgba(0,163,224,0.1)" }}
              onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent" }}
              title="New Chat"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
            </button>
            <button
              onClick={() => setIsSidebarOpen(false)}
              style={{
                background: "transparent", border: "none", cursor: "pointer", color: "#9CA3AF",
                padding: "6px", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.2s"
              }}
              onMouseOver={(e) => { e.currentTarget.style.color = "#4B5563"; e.currentTarget.style.background = "rgba(0,0,0,0.05)" }}
              onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent" }}
              title="Close Sidebar"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
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
                  <button
                    type="submit"
                    title="Save"
                    style={{
                      background: "transparent", border: "none", cursor: "pointer", color: "#10B981",
                      padding: "4px", borderRadius: "4px", display: "flex", alignItems: "center",
                      transition: "all 0.2s"
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = "rgba(16, 185, 129, 0.1)" }}
                    onMouseOut={(e) => { e.currentTarget.style.background = "transparent" }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  </button>
                  <button
                    type="button"
                    title="Cancel"
                    style={{
                      background: "transparent", border: "none", cursor: "pointer", color: "#EF4444",
                      padding: "4px", borderRadius: "4px", display: "flex", alignItems: "center",
                      transition: "all 0.2s"
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)" }}
                    onMouseOut={(e) => { e.currentTarget.style.background = "transparent" }}
                    onClick={(e) => { e.stopPropagation(); setEditingSessionId(null); }}
                  >
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
        position: "relative",
      }}>
        {/* Falling Aesthetic Lines */}
        <div className="lines-container">
          <div className="lines">
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
            <div className="line"></div>
          </div>
        </div>

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
          zIndex: 20, /* Header above background */
          position: "relative",
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
                gap: 6,
                background: "transparent",
                border: "none",
                borderRadius: 8,
                padding: "8px 12px",
                fontSize: 13,
                fontWeight: 600,
                color: "#9CA3AF",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseOver={(e) => { e.currentTarget.style.color = "#00A3E0"; e.currentTarget.style.background = "rgba(0,163,224,0.1)"; }}
              onMouseOut={(e) => { e.currentTarget.style.color = "#9CA3AF"; e.currentTarget.style.background = "transparent"; }}
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
          position: "relative",
          zIndex: 10, /* Messages above background */
        }}>
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            messages.map((msg) => (
              <div key={msg.id} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <Bubble msg={msg} onVerify={handleVerify} onCancelEdit={handleCancelEdit} onEditPayload={handleEditPayload} />
              </div>
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
          zIndex: 20, /* Input area above background */
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

                {/* Mic Button */}
                <button
                  onClick={toggleListening}
                  title={isListening ? "Stop listening" : "Start voice typing"}
                  className={`mic-btn ${isListening ? "is-listening" : ""}`}
                  style={{
                    background: isListening ? "rgba(239, 68, 68, 0.1)" : "none",
                    border: isListening ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(0,0,0,0.1)",
                    borderRadius: "50%",
                    width: 36,
                    height: 36,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    transition: "background 0.2s, border-color 0.2s",
                    marginRight: 8,
                  }}
                >
                  <svg className="mic-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={isListening ? "#EF4444" : "#6B7280"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="22"></line>
                  </svg>
                </button>

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
