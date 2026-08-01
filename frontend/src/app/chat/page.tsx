"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getToken,
  chatStream,
  getConversations,
  createConversation,
  getConversationMessages,
} from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

interface ConversationInfo {
  id: number;
  title: string;
  created_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "0",
      role: "assistant",
      content:
        "Hello! I am your Enterprise AI Operating System. I'm backed by a LangGraph Multi-Agent network (Planner, RAG, Reasoning, Code, Analytics). Ask me anything, and I will orchestrate retrieval and reasoning to compile an answer.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchConversations = useCallback(async () => {
    try {
      const list = await getConversations();
      setConversations(list);
      if (list.length > 0 && activeConvId === null) {
        // Auto-select latest conversation
        handleSelectConversation(list[0].id);
      }
    } catch {
      // ignore auth issues
    }
  }, [activeConvId]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetchConversations();
  }, [router, fetchConversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSelectConversation = async (id: number) => {
    setActiveConvId(id);
    setLoading(true);
    setError("");
    try {
      const history = await getConversationMessages(id);
      if (history.length === 0) {
        setMessages([
          {
            id: "0",
            role: "assistant",
            content: "Thread initialized. How can I help you today?",
          },
        ]);
      } else {
        setMessages(
          history.map((msg: any) => ({
            id: msg.id.toString(),
            role: msg.role,
            content: msg.content,
          }))
        );
      }
    } catch (err: any) {
      setError("Failed to load thread messages.");
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    setLoading(true);
    try {
      const newConv = await createConversation();
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([
        {
          id: "0",
          role: "assistant",
          content: "New chat thread created. Send a message to start.",
        },
      ]);
    } catch (err: any) {
      setError("Failed to initialize new conversation.");
    } finally {
      setLoading(false);
    }
  };

  const handleSend = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!input.trim() || loading) return;
      setError("");

      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: input,
      };

      const aiMessageId = (Date.now() + 1).toString();
      const aiMessage: Message = {
        id: aiMessageId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMessage, aiMessage]);
      setInput("");
      setLoading(true);

      try {
        await chatStream(
          userMessage.content,
          activeConvId,
          // onToken
          (token) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: msg.content + token }
                  : msg
              )
            );
          },
          // onDone
          (fullText, returnedConvId) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: fullText || msg.content, streaming: false }
                  : msg
              )
            );
            setLoading(false);
            if (activeConvId === null) {
              setActiveConvId(returnedConvId);
            }
            fetchConversations();
            inputRef.current?.focus();
          },
          // onError
          (errMsg) => {
            setError(errMsg);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: "Sorry, I encountered an error. Please try again.",
                      streaming: false,
                    }
                  : msg
              )
            );
            setLoading(false);
          }
        );
      } catch (err: any) {
        setError(err.message || "Stream failed");
        setLoading(false);
      }
    },
    [input, loading, activeConvId, fetchConversations]
  );

  const suggestions = [
    "Summarize everything discussed about Project Alpha over the last six months, identify risks, compare with previous quarters, analyze code changes, and generate an executive report.",
    "Draft a Weekly Progress Report including recent Jira tasks and commits.",
    "Compare the terms and conditions in our uploaded corporate contracts.",
    "Analyze recent system performance logs and cost analytics."
  ];

  return (
    <div className="flex h-screen bg-[#060814] text-white">
      {/* Sidebar - Threads */}
      <aside className="w-80 border-r border-white/[0.06] bg-[#0a0e1a]/80 backdrop-blur-xl flex flex-col shrink-0">
        <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/10">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <span className="font-bold text-sm bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Operating Threads
            </span>
          </div>
          <button
            onClick={handleNewConversation}
            className="p-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] text-slate-300 transition-all"
            title="New Conversation"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => handleSelectConversation(c.id)}
              className={`w-full text-left px-3.5 py-3 rounded-xl transition-all duration-200 flex items-start gap-3 group border ${
                activeConvId === c.id
                  ? "bg-white/[0.05] border-indigo-500/30 text-white"
                  : "bg-transparent border-transparent text-slate-400 hover:bg-white/[0.02] hover:text-slate-200"
              }`}
            >
              <span className="text-base shrink-0 mt-0.5">💬</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold truncate leading-normal">
                  {c.title || "New Thread"}
                </p>
                <p className="text-[10px] text-slate-600 mt-1">
                  ID: {c.id} • {new Date(c.created_at).toLocaleDateString()}
                </p>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Main chat window */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="backdrop-blur-xl bg-[#0a0e1a]/85 border-b border-white/[0.06] px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors text-sm px-2.5 py-1.5 rounded-xl hover:bg-white/[0.04]"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              Go to Dashboard
            </Link>
            <div className="w-px h-5 bg-white/[0.08]" />
            <div>
              <h2 className="text-sm font-bold text-white">Multi-Agent RAG Workspace</h2>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Model: llama-3.3-70b-versatile • Security: ABAC Enabled
              </p>
            </div>
          </div>
        </header>

        {/* Message area */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-sm shrink-0 mt-0.5 shadow-md shadow-indigo-500/20">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
              )}
              <div
                className={`max-w-[75%] px-5 py-4 rounded-2xl text-sm leading-relaxed border ${
                  msg.role === "user"
                    ? "bg-gradient-to-r from-indigo-600 to-violet-600 border-indigo-500/20 text-white rounded-br-none shadow-lg shadow-indigo-500/10"
                    : "bg-white/[0.03] border-white/[0.06] text-slate-200 rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-wrap">
                  {msg.content}
                  {msg.streaming && (
                    <span className="inline-block w-2.5 h-4 ml-1 bg-indigo-400 animate-pulse rounded-sm" />
                  )}
                </div>
              </div>
              {msg.role === "user" && (
                <div className="w-9 h-9 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-sm shrink-0 mt-0.5">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
              )}
            </div>
          ))}

          {loading && messages[messages.length - 1]?.content === "" && (
            <div className="flex gap-4 justify-start">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-sm shrink-0 shadow-md shadow-indigo-500/20">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div className="bg-white/[0.03] border border-white/[0.06] px-5 py-4 rounded-2xl rounded-bl-none">
                <div className="flex gap-1.5 items-center h-4">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/80 animate-bounce [animation-delay:0ms]" />
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/80 animate-bounce [animation-delay:150ms]" />
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/80 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2.5 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 max-w-xl mx-auto">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* Suggestions */}
        {messages.length <= 1 && (
          <div className="px-6 pb-4 max-w-4xl w-full mx-auto">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold mb-2.5">
              Execute Decomposed Workflow Queries
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                  className="text-left text-xs text-slate-400 hover:text-white px-4 py-3 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-indigo-500/30 transition-all duration-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer input */}
        <footer className="backdrop-blur-xl bg-[#0a0e1a]/85 border-t border-white/[0.06] px-6 py-4 shrink-0">
          <form onSubmit={handleSend} className="relative max-w-5xl mx-auto">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Deploy complex agentic queries across vector documents, git history, and graph databases..."
              disabled={loading}
              className="w-full pl-5 pr-14 py-4 bg-white/[0.04] border border-white/[0.08] rounded-xl focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/40 outline-none transition-all text-xs text-white placeholder-slate-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-2.5 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-all group"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-lg opacity-100 group-hover:from-indigo-500 group-hover:to-violet-500 group-disabled:opacity-50 transition-all" />
              <svg
                className="relative z-10"
                xmlns="http://www.w3.org/2000/svg"
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2.5"
              >
                <path d="m22 2-7 20-4-9-9-4Z" />
                <path d="M22 2 11 13" />
              </svg>
            </button>
          </form>
          <p className="text-[10px] text-slate-500 mt-2 text-center">
            Multi-Agent system decomposes query tasks dynamically via Graph State routing pipelines.
          </p>
        </footer>
      </div>
    </div>
  );
}
