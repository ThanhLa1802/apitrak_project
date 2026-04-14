import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { createDeviceIcon, fmt, formatTs } from "./DeviceMarker";
import TrackLayer from "./TrackLayer";
import type { Device, Asset, LivePosition, LocationRecordFeature } from "../../types";

// ── Persist map view across page reloads ─────────────────────────────────────

const MAP_VIEW_KEY = "apitrak:map-view";

interface SavedView { lat: number; lng: number; zoom: number; }

function readSavedView(): SavedView | null {
    try {
        const raw = localStorage.getItem(MAP_VIEW_KEY);
        return raw ? (JSON.parse(raw) as SavedView) : null;
    } catch {
        return null;
    }
}

function MapViewPersister() {
    useMapEvents({
        moveend(e) {
            const { lat, lng } = e.target.getCenter();
            const zoom = e.target.getZoom();
            localStorage.setItem(MAP_VIEW_KEY, JSON.stringify({ lat, lng, zoom }));
        },
    });
    return null;
}

// ── Geofence overlay component ───────────────────────────────────────────────

interface GeofenceLayerProps {
    geojson: GeoJSON.FeatureCollection | null;
}

function GeofenceLayer({ geojson }: GeofenceLayerProps) {
    const map = useMap();

    useEffect(() => {
        if (!geojson) return;
        const layer = L.geoJSON(geojson, {
            style: { color: "#8B5CF6", weight: 2, fillOpacity: 0.1 },
        }).addTo(map);
        return () => { map.removeLayer(layer); };
    }, [map, geojson]);

    return null;
}

// ── Device markers ────────────────────────────────────────────────────────────

interface DeviceMarkersProps {
    positions: Map<string, LivePosition>;
    deviceMap: Map<string, Device>;
    assetMap: Map<string, Asset>;
    selectedDeviceId: string | null;
}

function DeviceMarkers({
    positions,
    deviceMap,
    assetMap,
    selectedDeviceId,
}: DeviceMarkersProps) {
    return (
        <>
            {Array.from(positions.values()).map((pos) => {
                const lat = parseFloat(pos.lat);
                const lng = parseFloat(pos.lng);
                if (isNaN(lat) || isNaN(lng)) return null;

                const device = deviceMap.get(pos.device_id);
                const asset = device ? assetMap.get(device.asset) : undefined;
                const heading = pos.heading ? parseFloat(pos.heading) : null;
                const isSelected = pos.device_id === selectedDeviceId;

                return (
                    <Marker
                        key={pos.device_id}
                        position={[lat, lng]}
                        icon={createDeviceIcon(heading, isSelected)}
                    >
                        <Popup>
                            <div className="text-xs space-y-1 min-w-[140px]">
                                <p className="font-semibold text-sm">{asset?.name ?? "Unknown device"}</p>
                                <p className="text-gray-500">{device?.serial_number ?? pos.device_id}</p>
                                <hr />
                                <p>Speed: {fmt(pos.speed, " km/h")}</p>
                                <p>Heading: {fmt(pos.heading, "°", 0)}</p>
                                <p>Battery: {fmt(pos.battery, "%", 0)}</p>
                                <p className="text-gray-400">Updated: {formatTs(pos.ts)}</p>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </>
    );
}

// ── Main LiveMap ──────────────────────────────────────────────────────────────

interface Props {
    positions: Map<string, LivePosition>;
    deviceMap: Map<string, Device>;
    assetMap: Map<string, Asset>;
    trackFeatures: LocationRecordFeature[];
    geofencesGeojson: GeoJSON.FeatureCollection | null;
    selectedDeviceId: string | null;
    showGeofences: boolean;
}

const DEFAULT_CENTER: [number, number] = [20, 0];
const DEFAULT_ZOOM = 3;
const DEVICE_ZOOM = 15;

export default function LiveMap({
    positions,
    deviceMap,
    assetMap,
    trackFeatures,
    geofencesGeojson,
    selectedDeviceId,
    showGeofences,
}: Props) {
    const mapRef = useRef<L.Map | null>(null);
    // Keep a ref so the flyTo effect can read the latest positions
    // without adding positions to the dep array (which would re-fly on every ping)
    const positionsRef = useRef(positions);
    positionsRef.current = positions;

    // Fly to device ONCE when selectedDeviceId changes, not on every ping
    useEffect(() => {
        if (!selectedDeviceId || !mapRef.current) return;
        const pos = positionsRef.current.get(selectedDeviceId);
        if (!pos) return;
        const lat = parseFloat(pos.lat);
        const lng = parseFloat(pos.lng);
        if (!isNaN(lat) && !isNaN(lng)) {
            mapRef.current.flyTo([lat, lng], DEVICE_ZOOM, { duration: 1.2 });
        }
    }, [selectedDeviceId]);

    const saved = readSavedView();

    return (
        <MapContainer
            center={saved ? [saved.lat, saved.lng] : DEFAULT_CENTER}
            zoom={saved ? saved.zoom : DEFAULT_ZOOM}
            className="h-full w-full"
            ref={mapRef}
        >
            <MapViewPersister />
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
            />

            {showGeofences && <GeofenceLayer geojson={geofencesGeojson} />}

            <DeviceMarkers
                positions={positions}
                deviceMap={deviceMap}
                assetMap={assetMap}
                selectedDeviceId={selectedDeviceId}
            />

            <TrackLayer features={trackFeatures} />
        </MapContainer>
    );
}
