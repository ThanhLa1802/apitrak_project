import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { useWebSocket } from "./useWebSocket";
import type { LiveMapResponse, LivePosition, OrgScopeTokenResponse, WsMessage } from "../types";

export function useLivePositions(
    orgId: string | null,
    orgToken: string | null,
): {
    positions: Map<string, LivePosition>;
    geofenceAlerts: { device_id: string; geofence_id: string; event: string }[];
} {
    const [positions, setPositions] = useState<Map<string, LivePosition>>(new Map());
    const [geofenceAlerts, setGeofenceAlerts] = useState<
        { device_id: string; geofence_id: string; event: string }[]
    >([]);

    const { data: initialData } = useQuery({
        queryKey: ["live-positions", orgId],
        queryFn: () =>
            api.get<LiveMapResponse>(`/api/v1/map/${orgId}/live/`).then((r: { data: LiveMapResponse }) => r.data),
        enabled: !!orgId,
        staleTime: 0,
        refetchOnWindowFocus: false,
    });

    // Seed from initial REST fetch
    useEffect(() => {
        if (!initialData) return;
        setPositions(() => {
            const m = new Map<string, LivePosition>();
            for (const d of initialData.devices) {
                m.set(d.device_id, d);
            }
            return m;
        });
    }, [initialData]);

    const handleMessage = (msg: WsMessage) => {
        if (msg.type === "location_update") {
            setPositions((prev: Map<string, LivePosition>) => {
                const next = new Map(prev);
                next.set(msg.device_id, {
                    device_id: msg.device_id,
                    lat: msg.lat,
                    lng: msg.lng,
                    ts: msg.timestamp,
                    speed: msg.speed,
                    heading: msg.heading,
                    accuracy: null,
                    battery: msg.battery,
                });
                return next;
            });
        } else if (msg.type === "geofence_event") {
            setGeofenceAlerts((prev: { device_id: string; geofence_id: string; event: string }[]) => [
                { device_id: msg.device_id, geofence_id: msg.geofence_id, event: msg.event },
                ...prev.slice(0, 19),
            ]);
        }
    };

    const { setOrgContext, orgName } = useAuthStore();

    // Called by useWebSocket when org token is rejected (expired).
    // Silently re-issues the org-scope JWT using the still-valid access token.
    // If the access token is also expired, api.ts will attempt a refresh;
    // if that fails too, it calls logout() automatically.
    const handleTokenExpired = useCallback(async () => {
        if (!orgId || !orgName) return;
        const { data } = await api.post<OrgScopeTokenResponse>(
            "/api/v1/token/org-scope/",
            { org_id: orgId },
        );
        setOrgContext(orgId, orgName, data.token);
    }, [orgId, orgName, setOrgContext]);

    useWebSocket(orgId, orgToken, handleMessage, handleTokenExpired);

    return { positions, geofenceAlerts };
}
