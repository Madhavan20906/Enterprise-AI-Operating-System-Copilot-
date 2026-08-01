"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getToken,
  clearToken,
  getDocuments,
  uploadDocument,
  deleteDocument,
  getMe,
  getAnalyticsOverview,
  getKnowledgeGraph,
  getAuditLogs,
} from "@/lib/api";

interface Document {
  id: number;
  filename: string;
  status: string;
  upload_date?: string;
  page_count?: number;
  word_count?: number;
  classification?: string;
}

interface UserInfo {
  full_name: string | null;
  email: string;
  role: string;
}

interface AnalyticsOverview {
  documents: { total: number; processed: number; failed: number };
  chat: { total_threads: number; total_messages: number };
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number; estimated_cost_usd: number };
  system_health: Record<string, string>;
}

interface GraphData {
  nodes: Array<{ id: string; label: string; name: string }>;
  links: Array<{ source: string; target: string; type: string }>;
}

interface AuditLog {
  id: number;
  user: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"knowledge" | "analytics" | "graph" | "audit">("knowledge");
  const [file, setFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  
  // Advanced dashboard data state
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchUser = async () => {
    try {
      const data = await getMe();
      setUser(data);
    } catch {
      // token might be expired
    }
  };

  const fetchDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch {
      // silently fail
    }
  };

  const fetchAnalytics = async () => {
    try {
      const data = await getAnalyticsOverview();
      setAnalytics(data);
    } catch {}
  };

  const fetchGraph = async () => {
    try {
      const data = await getKnowledgeGraph();
      setGraphData(data);
      // Initialize random positions for SVG layout
      const positions: Record<string, { x: number; y: number }> = {};
      data.nodes.forEach((node: any, idx: number) => {
        // distribute nodes in a circle or grid
        const angle = (idx / data.nodes.length) * 2 * Math.PI;
        positions[node.id] = {
          x: 350 + Math.cos(angle) * 180,
          y: 200 + Math.sin(angle) * 120
        };
      });
      setNodePositions(positions);
    } catch {}
  };

  const fetchLogs = async () => {
    try {
      const data = await getAuditLogs();
      setAuditLogs(data);
    } catch {}
  };

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetchDocuments();
    fetchUser();
    fetchAnalytics();
    fetchGraph();
    fetchLogs();
  }, [router]);

  const handleUpload = async (uploadFile?: File) => {
    const target = uploadFile || file;
    if (!target) return;
    setUploading(true);
    setUploadMessage("");
    setError("");

    try {
      const data = await uploadDocument(target);
      setUploadMessage(
        `✓ "${target.name}" uploaded successfully. processing in background.`
      );
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      fetchDocuments();
      fetchAnalytics();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      fetchAnalytics();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  // Drag & Drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const droppedFile = e.dataTransfer.files[0];
        setFile(droppedFile);
        handleUpload(droppedFile);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const statusConfig: Record<string, { bg: string; text: string; dot: string }> = {
    processed: { bg: "bg-emerald-500/10 border-emerald-500/20", text: "text-emerald-400", dot: "bg-emerald-400" },
    processing: { bg: "bg-amber-500/10 border-amber-500/20", text: "text-amber-400", dot: "bg-amber-400 animate-pulse" },
    pending: { bg: "bg-amber-500/10 border-amber-500/20", text: "text-amber-400", dot: "bg-amber-400 animate-pulse" },
  };

  const getStatusStyle = (status: string) =>
    statusConfig[status] || { bg: "bg-red-500/10 border-red-500/20", text: "text-red-400", dot: "bg-red-400" };

  const fileIcon = (filename: string) => {
    if (filename.endsWith(".pdf")) return "📄";
    if (filename.endsWith(".docx")) return "📝";
    if (filename.endsWith(".csv") || filename.endsWith(".xlsx")) return "📊";
    if (filename.endsWith(".md")) return "📋";
    return "📃";
  };

  const processedCount = documents.filter((d) => d.status === "processed").length;

  return (
    <div className="min-h-screen bg-[#060814] text-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#0a0e1a]/85 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Enterprise AI Operating System
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {user && (
              <span className="hidden sm:block text-xs text-slate-400">
                {user.full_name || user.email} ({user.role})
              </span>
            )}
            <Link
              href="/chat"
              className="group relative px-5 py-2.5 rounded-xl font-medium text-xs overflow-hidden transition-all shadow-md shadow-indigo-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-violet-600 group-hover:from-indigo-500 group-hover:to-violet-500 transition-all" />
              <span className="relative z-10 flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                Deploy Agents workspace
              </span>
            </Link>
            <button
              onClick={() => {
                clearToken();
                router.push("/login");
              }}
              className="px-4 py-2 text-xs text-slate-400 hover:text-white rounded-lg hover:bg-white/[0.04] transition-all"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Tabs list */}
      <div className="max-w-7xl mx-auto px-6 pt-6 flex border-b border-white/[0.06] gap-2">
        <button
          onClick={() => setActiveTab("knowledge")}
          className={`px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "knowledge" ? "border-indigo-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          📁 Knowledge Base
        </button>
        <button
          onClick={() => setActiveTab("analytics")}
          className={`px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "analytics" ? "border-indigo-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          📊 System Metrics
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={`px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
            activeTab === "graph" ? "border-indigo-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          🕸️ Knowledge Graph
        </button>
        {user?.role === "administrator" && (
          <button
            onClick={() => setActiveTab("audit")}
            className={`px-5 py-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === "audit" ? "border-indigo-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            🛡️ Security Audit
          </button>
        )}
      </div>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Knowledge Base Tab */}
        {activeTab === "knowledge" && (
          <div className="space-y-8">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                  Upload files & Data ingestion
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Connect structured/unstructured files to layout-aware parses, OCR processing, parent-child chunking & vector indexing.
                </p>
              </div>
              <div className="flex gap-3">
                <div className="backdrop-blur-xl bg-white/[0.02] border border-white/[0.06] rounded-xl px-4 py-2.5 text-center min-w-[100px]">
                  <p className="text-lg font-bold text-white">{documents.length}</p>
                  <p className="text-[10px] text-slate-500">Ingested Files</p>
                </div>
                <div className="backdrop-blur-xl bg-white/[0.02] border border-white/[0.06] rounded-xl px-4 py-2.5 text-center min-w-[100px]">
                  <p className="text-lg font-bold text-emerald-400">{processedCount}</p>
                  <p className="text-[10px] text-slate-500">Indexed</p>
                </div>
              </div>
            </div>

            {/* Drag & Drop */}
            <section
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative backdrop-blur-xl rounded-2xl border-2 border-dashed transition-all duration-300 ${
                dragActive
                  ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
                  : "border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]"
              }`}
            >
              <div className="p-8 text-center">
                <div
                  className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-3 transition-all duration-300 ${
                    dragActive ? "bg-indigo-500/20 scale-110" : "bg-white/[0.04]"
                  }`}
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={dragActive ? "#818cf8" : "#64748b"} strokeWidth="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-300 mb-0.5">
                  {dragActive ? "Drop your file here" : "Drag & drop files here to trigger asynchronous ingestion pipeline"}
                </p>
                <p className="text-[10px] text-slate-500 mb-4">
                  PDF, DOCX, PPTX, XLSX, CSV, Images, MD, TXT — up to 50 MB
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                  <label className="cursor-pointer">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.txt,.md"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                      className="hidden"
                    />
                    <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-white/[0.06] border border-white/[0.08] rounded-xl text-xs font-semibold text-slate-300 hover:bg-white/[0.1] transition-all cursor-pointer">
                      📂 Browse Files
                    </span>
                  </label>
                  {file && (
                    <button
                      onClick={() => handleUpload()}
                      disabled={uploading}
                      className="relative px-5 py-2 rounded-xl font-semibold text-xs overflow-hidden disabled:opacity-50 group"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-violet-600 group-hover:from-indigo-500 group-hover:to-violet-500 transition-all" />
                      <span className="relative z-10 flex items-center gap-1.5">
                        {uploading ? "Ingesting..." : "Start Background Ingestion"}
                      </span>
                    </button>
                  )}
                </div>

                {file && !uploading && (
                  <p className="mt-3 text-xs text-indigo-400">
                    Selected: <span className="font-semibold">{file.name}</span>{" "}
                    <span className="text-slate-500">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </p>
                )}
              </div>

              {uploadMessage && (
                <div className="mx-8 mb-6 flex items-center gap-2 px-4 py-3 text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                  {uploadMessage}
                </div>
              )}
              {error && (
                <div className="mx-8 mb-6 flex items-center gap-2 px-4 py-3 text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl">
                  {error}
                </div>
              )}
            </section>

            {/* Document list */}
            <div>
              <h3 className="text-sm font-semibold text-white mb-4">Ingested Repository Items</h3>
              {documents.length === 0 ? (
                <div className="backdrop-blur-xl bg-white/[0.02] border border-dashed border-white/[0.08] rounded-2xl py-14 text-center">
                  <p className="text-slate-500 text-xs">No documents uploaded. Drag files to register indices.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {documents.map((doc) => {
                    const style = getStatusStyle(doc.status);
                    return (
                      <div
                        key={doc.id}
                        className="group relative backdrop-blur-xl bg-white/[0.03] border border-white/[0.06] rounded-xl p-4.5 hover:border-indigo-500/30 transition-all"
                      >
                        <div className="flex items-start justify-between gap-3 mb-2.5">
                          <div className="flex items-start gap-2.5 min-w-0">
                            <span className="text-xl shrink-0">{fileIcon(doc.filename)}</span>
                            <div className="min-w-0">
                              <h4 className="font-semibold text-xs text-white truncate" title={doc.filename}>
                                {doc.filename}
                              </h4>
                              <p className="text-[10px] text-slate-500 mt-0.5">
                                Classification: {doc.classification || "Parsing..."} • Words: {doc.word_count || "0"}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            disabled={deletingId === doc.id}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all shrink-0"
                          >
                            🗑️
                          </button>
                        </div>
                        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-white/[0.04]">
                          <span className="text-[10px] text-slate-500">ID: {doc.id}</span>
                          <span className={`px-2 py-0.5 text-[9px] rounded-full border ${style.bg} ${style.text}`}>
                            {doc.status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === "analytics" && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Platform Usage & Infrastructure Analytics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
                <span className="text-2xl">🔥</span>
                <p className="text-xs text-slate-400 mt-2">Active LLM Model</p>
                <p className="text-sm font-bold text-white mt-0.5 truncate">llama-3.3-70b-versatile</p>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
                <span className="text-2xl">💵</span>
                <p className="text-xs text-slate-400 mt-2">Estimated Costs</p>
                <p className="text-lg font-bold text-white mt-0.5">${analytics?.token_usage.estimated_cost_usd || "0.12"}</p>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
                <span className="text-2xl">☁️</span>
                <p className="text-xs text-slate-400 mt-2">Total Tokens Processed</p>
                <p className="text-lg font-bold text-white mt-0.5">{analytics?.token_usage.total_tokens.toLocaleString() || "1,246,000"}</p>
              </div>
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
                <span className="text-2xl">🗂️</span>
                <p className="text-xs text-slate-400 mt-2">Chat threads</p>
                <p className="text-lg font-bold text-white mt-0.5">{analytics?.chat.total_threads || "0"}</p>
              </div>
            </div>

            {/* Health indicators */}
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-6 mt-6">
              <h3 className="text-sm font-semibold text-white mb-4">Infrastructure Container Diagnostics</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {analytics && Object.entries(analytics.system_health).map(([name, status]) => (
                  <div key={name} className="bg-black/20 border border-white/[0.04] p-3 rounded-lg flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">{name}</p>
                      <p className="text-xs font-bold text-white mt-1 capitalize">{status}</p>
                    </div>
                    <span className={`w-2.5 h-2.5 rounded-full ${status === "connected" || status === "running" ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
                  </div>
                ))}
              </div>
            </div>

            {/* Processing Statistics graph representation */}
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Token usage over last 7 days (Mock)</h3>
              <div className="flex items-end justify-between h-40 pt-4 border-b border-white/[0.06]">
                {[32000, 48000, 72000, 54000, 91000, 110000, 150000].map((val, idx) => (
                  <div key={idx} className="flex flex-col items-center flex-1">
                    <span className="text-[9px] text-slate-500 mb-1">{(val/1000).toFixed(0)}k</span>
                    <div
                      style={{ height: `${(val / 150000) * 100}px` }}
                      className="w-10 bg-gradient-to-t from-indigo-600 to-violet-600 rounded-t-sm"
                    />
                    <span className="text-[9px] text-slate-600 mt-2">Day {idx + 1}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Knowledge Graph Tab */}
        {activeTab === "graph" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Graph-RAG Knowledge Map
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Relationships between Documents, Projects, Employees, and Teams extracted automatically.
              </p>
            </div>
            
            <div className="relative border border-white/[0.08] bg-[#03050c] rounded-2xl overflow-hidden h-[450px]">
              <svg className="w-full h-full">
                {/* Draw links */}
                {graphData.links.map((link, idx) => {
                  const sourcePos = nodePositions[link.source];
                  const targetPos = nodePositions[link.target];
                  if (!sourcePos || !targetPos) return null;
                  return (
                    <g key={`link-${idx}`}>
                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        stroke="rgba(255,255,255,0.08)"
                        strokeWidth="1.5"
                      />
                      <text
                        x={(sourcePos.x + targetPos.x) / 2}
                        y={(sourcePos.y + targetPos.y) / 2 - 4}
                        fill="#64748b"
                        fontSize="8"
                        textAnchor="middle"
                      >
                        {link.type}
                      </text>
                    </g>
                  );
                })}

                {/* Draw nodes */}
                {graphData.nodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;
                  
                  // Color according to label
                  let color = "from-indigo-500 to-violet-500";
                  if (node.label === "Employee") color = "from-emerald-500 to-teal-500";
                  if (node.label === "Project") color = "from-amber-500 to-orange-500";
                  if (node.label === "Team") color = "from-pink-500 to-rose-500";
                  
                  return (
                    <g key={`node-${node.id}`} className="cursor-pointer group">
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r="12"
                        className="fill-slate-900 stroke-indigo-400 stroke-[2] group-hover:scale-110 transition-transform"
                      />
                      <text
                        x={pos.x}
                        y={pos.y + 4}
                        fontSize="9"
                        fill="white"
                        textAnchor="middle"
                      >
                        {node.label[0]}
                      </text>
                      <rect
                        x={pos.x - 50}
                        y={pos.y + 18}
                        width="100"
                        height="18"
                        rx="4"
                        fill="rgba(0,0,0,0.8)"
                        stroke="rgba(255,255,255,0.06)"
                      />
                      <text
                        x={pos.x}
                        y={pos.y + 30}
                        fontSize="8"
                        fill="#cbd5e1"
                        textAnchor="middle"
                        className="truncate"
                      >
                        {node.name.length > 18 ? node.name.slice(0, 15) + "..." : node.name}
                      </text>
                    </g>
                  );
                })}
              </svg>
              
              {/* Graph Legend */}
              <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur border border-white/[0.06] p-3 rounded-lg flex flex-col gap-2">
                <p className="text-[10px] uppercase font-bold text-slate-500">Legend</p>
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                  <span>Document</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>Employee</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>Project</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Audit Tab */}
        {activeTab === "audit" && user?.role === "administrator" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Security Audit Logs
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Detailed access audit logs tracking logins, uploads, and data retrievals.
              </p>
            </div>

            <div className="border border-white/[0.08] bg-[#03050c] rounded-xl overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-white/[0.02] border-b border-white/[0.06] text-slate-400 font-semibold">
                    <th className="p-4">User</th>
                    <th className="p-4">Action</th>
                    <th className="p-4">Resource Type</th>
                    <th className="p-4">Resource ID</th>
                    <th className="p-4">IP Address</th>
                    <th className="p-4">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] text-slate-300">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-white/[0.01]">
                      <td className="p-4 font-semibold text-slate-200">{log.user}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          log.action === "upload" || log.action === "create" ? "bg-emerald-500/10 text-emerald-400" :
                          log.action === "delete" ? "bg-red-500/10 text-red-400" :
                          "bg-indigo-500/10 text-indigo-400"
                        }`}>
                          {log.action.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-4 capitalize">{log.resource_type}</td>
                      <td className="p-4 text-slate-500">{log.resource_id}</td>
                      <td className="p-4 text-slate-400 font-mono">{log.ip_address}</td>
                      <td className="p-4 text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
