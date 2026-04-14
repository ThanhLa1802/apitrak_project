import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet-draw";
import type { GeofenceFeature } from "../../types";

// ── Fly-to helper ─────────────────────────────────────────────────────────────

function FlyToGeofence({ selected }: { selected: GeofenceFeature | null }) {
    const map = useMap();
    useEffect(() => {
        if (!selected) return;
        const layer = L.geoJSON(selected as unknown as GeoJSON.Feature);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
        }
    }, [map, selected]);
    return null;
}

// ── Draw control inner component ──────────────────────────────────────────────

interface DrawControlProps {
    geofences: GeofenceFeature[];
    onCreated: (name: string, multipolygon: GeoJSON.MultiPolygon) => void;
    onDeleted: (id: string) => void;
}

function DrawControl({ geofences, onCreated, onDeleted }: DrawControlProps) {
    const map = useMap();
    const drawnItemsRef = useRef<L.FeatureGroup>(new L.FeatureGroup());
    const layerIdMapRef = useRef<Map<number, string>>(new Map());

    useEffect(() => {
        const drawnItems = drawnItemsRef.current;
        map.addLayer(drawnItems);

        const drawControl = new (L.Control as unknown as {
            new(opts: unknown): L.Control;
            Draw: new (opts: unknown) => L.Control;
        }).Draw({
            edit: { featureGroup: drawnItems },
            draw: {
                polygon: { allowIntersection: false },
                polyline: false,
                rectangle: false,
                circle: false,
                marker: false,
                circlemarker: false,
            },
        });
        map.addControl(drawControl);

        // Render existing geofences
        for (const feature of geofences) {
            const layer = L.geoJSON(feature as unknown as GeoJSON.Feature, {
                style: { color: "#8B5CF6", weight: 2, fillOpacity: 0.15 },
            });
            layer.eachLayer((l) => {
                drawnItems.addLayer(l);
                layerIdMapRef.current.set((l as unknown as { _leaflet_id: number })._leaflet_id, feature.properties.id);
            });
        }

        const handleCreated = (e: unknown) => {
            const event = e as { layer: L.Layer };
            drawnItems.addLayer(event.layer);
            const geoJson = (event.layer as unknown as { toGeoJSON: () => GeoJSON.Feature }).toGeoJSON();
            const multiPolygon: GeoJSON.MultiPolygon = {
                type: "MultiPolygon",
                coordinates: [(geoJson.geometry as GeoJSON.Polygon).coordinates],
            };
            const name = window.prompt("Geofence name:", "New Geofence") ?? "New Geofence";
            onCreated(name, multiPolygon);
            drawnItems.removeLayer(event.layer);
        };

        const handleDeleted = (e: unknown) => {
            const event = e as { layers: L.LayerGroup };
            event.layers.eachLayer((layer) => {
                const leafletId = (layer as unknown as { _leaflet_id: number })._leaflet_id;
                const id = layerIdMapRef.current.get(leafletId);
                if (id) onDeleted(id);
            });
        };

        map.on(L.Draw.Event.CREATED, handleCreated);
        map.on(L.Draw.Event.DELETED, handleDeleted);

        return () => {
            map.off(L.Draw.Event.CREATED, handleCreated);
            map.off(L.Draw.Event.DELETED, handleDeleted);
            map.removeControl(drawControl);
            map.removeLayer(drawnItems);
            drawnItems.clearLayers();
            layerIdMapRef.current.clear();
        };
        // Only re-run when geofences list identity changes
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map, geofences.length]);

    return null;
}

// ── Exported component ────────────────────────────────────────────────────────

interface Props {
    geofences: GeofenceFeature[];
    selected: GeofenceFeature | null;
    onCreated: (name: string, multipolygon: GeoJSON.MultiPolygon) => void;
    onDeleted: (id: string) => void;
}

const MAP_CENTER: [number, number] = [20, 0];

export default function GeofenceMap({ geofences, selected, onCreated, onDeleted }: Props) {
    return (
        <MapContainer center={MAP_CENTER} zoom={3} className="h-full w-full">
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
            />
            <DrawControl
                geofences={geofences}
                onCreated={onCreated}
                onDeleted={onDeleted}
            />
            <FlyToGeofence selected={selected} />
        </MapContainer>
    );
}
