import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";
import { api } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { useLivePositions } from "../hooks/useLivePositions";
import LiveMap from "../components/map/LiveMap";
import type {
    Device,
    Asset,
    PaginatedResponse,
    TrackResponse,
    GeofenceFeatureCollection,
    LocationRecordFeature,
} from "../types";

// ── Track panel ───────────────────────────────────────────────────────────────

interface TrackPanelProps {
    devices: Device[];
    assetMap: Map<string, Asset>;
    onTrackLoad: (features: LocationRecordFeature[]) => void;
    onTrackClear: () => void;
    selectedDeviceId: string | null;
    setSelectedDeviceId: (id: string | null) => void;
}

function TrackPanel({
    devices,
    assetMap,
    onTrackLoad,
    onTrackClear,
    selectedDeviceId,
    setSelectedDeviceId,
}: TrackPanelProps) {
    const [from, setFrom] = useState("");
    const [to, setTo] = useState("");
    const [loading, setLoading] = useState(false);

    const loadTrack = async () => {
        if (!selectedDeviceId) return;
        setLoading(true);
        try {
            const params = new URLSearchParams({ device: selectedDeviceId });
            if (from) params.set("from", new Date(from).toISOString());
            if (to) params.set("to", new Date(to).toISOString());

            const features: LocationRecordFeature[] = [];
            let cursor: string | null = `/api/v1/track/?${params}`;
            while (cursor) {
                const resp: AxiosResponse<TrackResponse> = await api.get<TrackResponse>(cursor);
                features.push(...resp.data.features);
                const nextUrl: string | null = resp.data.next;
                cursor = nextUrl ? new URL(nextUrl).pathname + new URL(nextUrl).search : null;
            }
            onTrackLoad(features);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Historical Track
            </h3>
            <select
                value={selectedDeviceId ?? ""}
                onChange={(e) => {
                    setSelectedDeviceId(e.target.value || null);
                    onTrackClear();
                }}
                className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
            >
                <option value="">— select device —</option>
                {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                        {assetMap.get(d.asset)?.name ?? d.serial_number}
                    </option>
                ))}
            </select>
            <div className="grid grid-cols-2 gap-2">
                <div>
                    <label className="mb-0.5 block text-xs text-gray-500">From</label>
                    <input
                        type="datetime-local"
                        value={from}
                        onChange={(e) => setFrom(e.target.value)}
                        className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    />
                </div>
                <div>
                    <label className="mb-0.5 block text-xs text-gray-500">To</label>
                    <input
                        type="datetime-local"
                        value={to}
                        onChange={(e) => setTo(e.target.value)}
                        className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    />
                </div>
            </div>
            <div className="flex gap-2">
                <button
                    onClick={loadTrack}
                    disabled={!selectedDeviceId || loading}
                    className="flex-1 rounded bg-blue-600 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                    {loading ? "Loading…" : "Load Track"}
                </button>
                <button
                    onClick={onTrackClear}
                    className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                >
                    Clear
                </button>
            </div>
        </div>
    );
}

// ── MapPage ───────────────────────────────────────────────────────────────────

export default function MapPage() {
    const { orgId, orgToken } = useAuthStore();
    const [trackFeatures, setTrackFeatures] = useState<LocationRecordFeature[]>([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
    const [showGeofences, setShowGeofences] = useState(true);
    const [panelTab, setPanelTab] = useState<"live" | "track">("live");

    const { positions, geofenceAlerts } = useLivePositions(orgId, orgToken);

    const { data: devicesData } = useQuery({
        queryKey: ["devices"],
        queryFn: () =>
            api.get<PaginatedResponse<Device>>("/api/v1/devices/").then((r) => r.data),
    });
    const devices = devicesData?.results ?? [];
    const deviceMap = new Map(devices.map((d) => [d.id, d]));

    const { data: assetsData } = useQuery({
        queryKey: ["assets"],
        queryFn: () =>
            api.get<PaginatedResponse<Asset>>("/api/v1/assets/").then((r) => r.data),
    });
    const assets = assetsData?.results ?? [];
    const assetMap = new Map(assets.map((a) => [a.id, a]));

    const { data: geofencesData } = useQuery({
        queryKey: ["geofences", orgId],
        queryFn: () =>
            api
                .get<GeofenceFeatureCollection>(`/api/v1/geofences/?org_id=${orgId}`)
                .then((r) => r.data),
        enabled: !!orgId,
    });

    return (
        <div className="relative flex h-full w-full">
            {/* Side panel */}
            <div className="absolute left-4 top-4 z-[1000] flex w-64 flex-col rounded-lg bg-white shadow-lg">
                {/* Tabs */}
                <div className="flex border-b">
                    {(["live", "track"] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setPanelTab(tab)}
                            className={`flex-1 py-2 text-xs font-medium capitalize ${panelTab === tab
                                    ? "border-b-2 border-blue-600 text-blue-600"
                                    : "text-gray-500 hover:text-gray-700"
                                }`}
                        >
                            {tab === "live" ? "Live" : "Track"}
                        </button>
                    ))}
                </div>

                <div className="p-3">
                    {panelTab === "live" ? (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                                    Online Devices ({positions.size})
                                </h3>
                                <label className="flex items-center gap-1 text-xs text-gray-500">
                                    <input
                                        type="checkbox"
                                        checked={showGeofences}
                                        onChange={(e) => setShowGeofences(e.target.checked)}
                                    />
                                    Fences
                                </label>
                            </div>
                            <div className="max-h-64 space-y-1 overflow-y-auto">
                                {positions.size === 0 ? (
                                    <p className="py-4 text-center text-xs text-gray-400">
                                        No active devices
                                    </p>
                                ) : (
                                    Array.from(positions.values()).map((pos) => {
                                        const device = deviceMap.get(pos.device_id);
                                        const asset = device ? assetMap.get(device.asset) : undefined;
                                        return (
                                            <button
                                                key={pos.device_id}
                                                onClick={() =>
                                                    setSelectedDeviceId(
                                                        selectedDeviceId === pos.device_id ? null : pos.device_id,
                                                    )
                                                }
                                                className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${selectedDeviceId === pos.device_id
                                                        ? "bg-blue-100 text-blue-800"
                                                        : "hover:bg-gray-100"
                                                    }`}
                                            >
                                                <span className="h-2 w-2 rounded-full bg-green-500" />
                                                <span className="flex-1 truncate font-medium">
                                                    {asset?.name ?? device?.serial_number ?? pos.device_id.slice(0, 8)}
                                                </span>
                                            </button>
                                        );
                                    })
                                )}
                            </div>

                            {/* Geofence alerts */}
                            {geofenceAlerts.length > 0 && (
                                <div className="border-t pt-2">
                                    <p className="mb-1 text-xs font-semibold text-gray-500">Recent Alerts</p>
                                    <div className="max-h-32 space-y-1 overflow-y-auto">
                                        {geofenceAlerts.slice(0, 5).map((a, i) => (
                                            <div
                                                key={i}
                                                className={`rounded px-2 py-1 text-xs ${a.event === "entered"
                                                        ? "bg-green-50 text-green-700"
                                                        : "bg-red-50 text-red-700"
                                                    }`}
                                            >
                                                {a.event === "entered" ? "↑" : "↓"}{" "}
                                                {deviceMap.get(a.device_id)?.serial_number ?? a.device_id.slice(0, 8)}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <TrackPanel
                            devices={devices}
                            assetMap={assetMap}
                            onTrackLoad={setTrackFeatures}
                            onTrackClear={() => setTrackFeatures([])}
                            selectedDeviceId={selectedDeviceId}
                            setSelectedDeviceId={setSelectedDeviceId}
                        />
                    )}
                </div>
            </div>

            {/* Map */}
            <LiveMap
                positions={positions}
                deviceMap={deviceMap}
                assetMap={assetMap}
                trackFeatures={trackFeatures}
                geofencesGeojson={geofencesData ?? null}
                selectedDeviceId={selectedDeviceId}
                showGeofences={showGeofences}
            />
        </div>
    );
}
