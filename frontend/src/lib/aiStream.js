// Streaming helper for the SSE ask endpoint. Uses fetch + ReadableStream so
// we can send our Bearer token via query param (EventSource can't set headers).
import { API_BASE, readSession } from "@/lib/api";

/**
 * askStream({ question, onDelta, onDone, onError, signal })
 *
 * Fires an SSE request to /api/ai/ask/stream and dispatches events:
 *   onDelta(text)               — per-token deltas
 *   onDone({ text, citations }) — final corrected text + resolved record refs
 *   onError(errorMessage)
 */
export const askStream = async ({ question, onDelta, onDone, onError, signal }) => {
    const session = readSession();
    if (!session?.token) {
        onError?.("Not authenticated.");
        return;
    }
    const url = `${API_BASE}/ai/ask/stream?question=${encodeURIComponent(question)}&token=${encodeURIComponent(session.token)}`;
    let resp;
    try {
        resp = await fetch(url, { signal, headers: { Accept: "text/event-stream" } });
    } catch (e) {
        onError?.(e?.message || "Network error");
        return;
    }
    if (!resp.ok || !resp.body) {
        onError?.(`Request failed (${resp.status})`);
        return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        // SSE messages are separated by a blank line
        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
            const raw = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const event = parseSseMessage(raw);
            if (!event) continue;
            if (event.event === "delta") {
                try {
                    const p = JSON.parse(event.data);
                    if (p?.text) onDelta?.(p.text);
                } catch { /* ignore */ }
            } else if (event.event === "done") {
                try {
                    const p = JSON.parse(event.data);
                    onDone?.(p);
                } catch {
                    onDone?.({ text: "", citations: [] });
                }
                return;
            } else if (event.event === "error") {
                try {
                    const p = JSON.parse(event.data);
                    onError?.(p?.detail || "Stream error");
                } catch {
                    onError?.("Stream error");
                }
                return;
            }
        }
    }
};

const parseSseMessage = (raw) => {
    const lines = raw.split("\n");
    let event = "message";
    let data = "";
    for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    return { event, data };
};
