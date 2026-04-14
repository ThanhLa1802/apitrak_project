import { useEffect, useRef, useCallback } from "react";
import type { WsMessage } from "../types";

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? "ws://localhost:8000";

const INITIAL_RETRY_MS = 1_000;
const MAX_RETRY_MS = 30_000;

export function useWebSocket(
    orgId: string | null,
    orgToken: string | null,
    onMessage: (msg: WsMessage) => void,
    onTokenExpired?: () => Promise<void>,
) {
    const wsRef = useRef<WebSocket | null>(null);
    const retryDelayRef = useRef(INITIAL_RETRY_MS);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const onMessageRef = useRef(onMessage);
    onMessageRef.current = onMessage;
    const onTokenExpiredRef = useRef(onTokenExpired);
    onTokenExpiredRef.current = onTokenExpired;
    // Track whether the connection was ever established for this attempt.
    // If onclose fires without onopen → server rejected (auth failure / 403).
    const wasConnectedRef = useRef(false);

    const connect = useCallback(() => {
        if (!orgId || !orgToken) return;

        const url = `${WS_URL}/ws/tracking/${orgId}/?token=${encodeURIComponent(orgToken)}`;
        const ws = new WebSocket(url);
        wsRef.current = ws;
        wasConnectedRef.current = false;

        ws.onopen = () => {
            wasConnectedRef.current = true;
            retryDelayRef.current = INITIAL_RETRY_MS;
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data as string) as WsMessage;
                onMessageRef.current(msg);
            } catch {
                // ignore malformed messages
            }
        };

        ws.onclose = (event) => {
            wsRef.current = null;
            if (!orgId || !orgToken) return;

            // Connection rejected without ever opening → likely expired token (403)
            const isAuthFailure = !wasConnectedRef.current && event.code === 1006;
            if (isAuthFailure && onTokenExpiredRef.current) {
                onTokenExpiredRef.current().then(() => {
                    // connect() will be re-triggered via useEffect when orgToken changes
                }).catch(() => {
                    // refresh failed → access token also dead → parent handles logout
                });
                return;
            }

            retryTimerRef.current = setTimeout(() => {
                retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_RETRY_MS);
                connect();
            }, retryDelayRef.current);
        };

        ws.onerror = () => {
            ws.close();
        };
    }, [orgId, orgToken]);

    useEffect(() => {
        connect();
        return () => {
            if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
            if (wsRef.current) {
                // Prevent reconnect on intentional close
                wsRef.current.onclose = null;
                wsRef.current.close();
            }
        };
    }, [connect]);
}
