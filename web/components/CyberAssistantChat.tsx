"use client";

import React, { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import AttackSurfaceLogo from "@/components/AttackSurfaceLogo";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  company?: {
    name: string;
    domain: string;
    id: number;
  };
  grounded_data?: {
    total_security_events?: number;
    total_cisa_items?: number;
    biggest_attack?: any;
    yearly_distribution?: Record<string, number>;
    attack_type_distribution?: Record<string, number>;
  };
}

const QUICK_PROMPTS = [
  "Biggest attack on Google in history and breakdown by years?",
  "What are the most exploited zero-days in CISA KEV right now?",
  "Analyze Microsoft's top attack vectors over the last 15 years",
  "Explain how modern supply chain attacks work (Log4j, libwebp)",
];

export default function CyberAssistantChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "### AttackSurface AI Threat Analyst (Gemini 3.6 Flash Grounded)\n\nI am your cybersecurity intelligence assistant, directly integrated with **1,705+ CISA KEV zero-days**, **3,750+ verified enterprise attack records**, and **20 years of threat telemetry**.\n\nAsk me anything — for example: *\"What was the biggest attack on Google in history and how many types of attacks were performed in which years?\"*",
      timestamp: "Ready",
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const res = await apiFetch<{
        response: string;
        company?: any;
        grounded_data?: any;
        model: string;
      }>("/api/v1/assistant/chat", {
        method: "POST",
        body: JSON.stringify({
          message: query,
          conversation_history: messages.map((m) => ({
            role: m.sender,
            content: m.text,
          })),
        }),
      });

      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: "assistant",
        text: res.response || "No intelligence report returned.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        company: res.company,
        grounded_data: res.grounded_data,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "assistant",
          text: `**Intelligence Connection Error:** ${err.message || "Failed to reach AI Threat Analyst engine."}`,
          timestamp: "Error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* ── Floating Launcher Trigger Button ── */}
      <div className="fixed bottom-12 right-6 z-40">
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          className="group relative flex items-center gap-3 px-4 py-2.5 rounded-full bg-slate-900/90 hover:bg-slate-800 border border-cyan-500/40 hover:border-cyan-400 text-white shadow-[0_0_20px_rgba(6,182,212,0.25)] hover:shadow-[0_0_25px_rgba(6,182,212,0.45)] backdrop-blur-md transition-all duration-200 cursor-pointer"
          title="Open AI Threat Analyst"
        >
          <AttackSurfaceLogo size="sm" showText={false} />
          <div className="flex flex-col text-left">
            <span className="text-[11px] font-mono font-bold tracking-wider text-cyan-300 uppercase">
              AI THREAT ANALYST
            </span>
            <span className="text-[9px] font-mono text-slate-400">
              GEMINI 3.6 FLASH · GROUNDED
            </span>
          </div>
          <svg className="w-4 h-4 text-cyan-400 group-hover:rotate-12 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </button>
      </div>

      {/* ── Slide-Over Chat Modal ── */}
      {isOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-slate-950 border-l border-slate-800/90 shadow-2xl flex flex-col backdrop-blur-xl animate-in slide-in-from-right duration-300">
          {/* Header */}
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
            <div className="flex items-center gap-3">
              <AttackSurfaceLogo size="sm" showText={false} />
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold tracking-wide text-white">AI CYBER THREAT ANALYST</h3>
                  <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    GEMINI 3.6
                  </span>
                </div>
                <p className="text-[10px] font-mono text-slate-400">
                  20-Year Intelligence Grounding · 1,705 KEV · 3,750+ Breaches
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setMessages([messages[0]])}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800 text-xs"
                title="Clear conversation"
              >
                Clear
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800"
                title="Close chat"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Quick Prompt Pills */}
          <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/30 overflow-x-auto flex gap-2 shrink-0 scrollbar-none">
            {QUICK_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSend(prompt)}
                disabled={loading}
                className="text-[10px] font-mono text-slate-300 hover:text-cyan-300 bg-slate-800/70 hover:bg-cyan-950/40 border border-slate-700 hover:border-cyan-500/50 px-2.5 py-1 rounded-full whitespace-nowrap transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
              >
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <span className="text-[10px] font-mono text-slate-500">
                    {m.sender === "user" ? "OPERATOR" : "THREAT ANALYST"}
                  </span>
                  <span className="text-[9px] font-mono text-slate-600">· {m.timestamp}</span>
                </div>
                <div
                  className={`max-w-[92%] rounded-xl p-3.5 leading-relaxed ${
                    m.sender === "user"
                      ? "bg-cyan-600/20 text-cyan-100 border border-cyan-500/40"
                      : "bg-slate-900/90 text-slate-200 border border-slate-800"
                  }`}
                >
                  <div className="whitespace-pre-wrap font-sans text-xs space-y-2">
                    {m.text}
                  </div>

                  {m.company && (
                    <div className="mt-3 pt-2.5 border-t border-slate-800 flex flex-wrap gap-2 text-[10px] font-mono">
                      <span className="px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/50">
                        Target: {m.company.name} ({m.company.domain})
                      </span>
                      {m.grounded_data?.total_security_events !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/50">
                          {m.grounded_data.total_security_events} Security Events
                        </span>
                      )}
                      {m.grounded_data?.total_cisa_items !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/50">
                          {m.grounded_data.total_cisa_items} KEV Zero-Days
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex flex-col items-start">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-cyan-400 font-mono text-xs">
                  <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                  <span>Synthesizing database records and querying Gemini 3.6 Flash...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="p-3 border-t border-slate-800 bg-slate-900/70">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about any company, attack history, or CVE..."
                disabled={loading}
                className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500/60 rounded-lg px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 font-sans"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-4 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs disabled:opacity-50 disabled:cursor-not-allowed font-mono transition-colors shrink-0"
              >
                SEND
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
