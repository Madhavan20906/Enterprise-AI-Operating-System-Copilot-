/**
 * Centralized API configuration for the Enterprise AI Copilot frontend.
 * All backend calls go through these helpers.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

/** Return the stored JWT, or null */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

/** Persist a JWT */
export function setToken(token: string) {
  localStorage.setItem("token", token);
}

/** Clear the JWT (logout) */
export function clearToken() {
  localStorage.removeItem("token");
}

/** Standard headers with JSON + Auth */
function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

// ─── Auth ──────────────────────────────────────────────

export async function login(email: string, password: string) {
  const res = await fetch(`${API_V1}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Invalid credentials");
  }
  return res.json();
}

export async function register(email: string, password: string, fullName: string) {
  const res = await fetch(`${API_V1}/users/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Registration failed");
  }
  return res.json();
}

export async function getMe() {
  const res = await fetch(`${API_V1}/users/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

// ─── Documents ──────────────────────────────────────────

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch(`${API_V1}/documents/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  } catch (err: any) {
    if (err.name === "TypeError" && err.message === "Failed to fetch") {
      throw new Error("Unable to reach backend server. Please verify backend is running on http://localhost:8000.");
    }
    throw err;
  }
}

export async function getDocuments() {
  const res = await fetch(`${API_V1}/documents/`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function deleteDocument(id: number) {
  const res = await fetch(`${API_V1}/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Delete failed");
  }
  return res.json();
}

// ─── Chat & Conversations ────────────────────────────────

export async function getConversations() {
  const res = await fetch(`${API_V1}/chat/conversations`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function createConversation() {
  const res = await fetch(`${API_V1}/chat/conversations`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function getConversationMessages(conversationId: number) {
  const res = await fetch(`${API_V1}/chat/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

export async function chatSync(query: string, conversationId?: number) {
  const res = await fetch(`${API_V1}/chat/`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Chat request failed");
  return data;
}

/**
 * Stream chat tokens via SSE.
 * Calls `onToken` for each token received, `onDone` when complete.
 */
export async function chatStream(
  query: string,
  conversationId: number | null,
  onToken: (token: string) => void,
  onDone: (fullText: string, conversationId: number) => void,
  onError: (error: string) => void,
) {
  const res = await fetch(`${API_V1}/chat/stream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    onError(data.detail || "Stream request failed");
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response stream available");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const payload = JSON.parse(line.slice(6));
          if (payload.error) {
            onError(payload.error);
            return;
          }
          if (payload.token) {
            onToken(payload.token);
          }
          if (payload.agent_step) {
            // Can be used to show running status of specialized agent
            onToken(`\n[Agent: ${payload.agent_step.agent.toUpperCase()} is executing...]\n`);
          }
          if (payload.done) {
            onDone(payload.full_text || "", payload.conversation_id);
            return;
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }
  }
}

// ─── Analytics ──────────────────────────────────────────

export async function getAnalyticsOverview() {
  const res = await fetch(`${API_V1}/analytics/overview`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch analytics");
  return res.json();
}

export async function getKnowledgeGraph() {
  const res = await fetch(`${API_V1}/analytics/graph`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch knowledge graph");
  return res.json();
}

export async function getAuditLogs() {
  const res = await fetch(`${API_V1}/analytics/audit-logs`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}
