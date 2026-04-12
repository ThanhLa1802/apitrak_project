import { Polyline, Popup, CircleMarker } from "react-leaflet";
import type { LocationRecordFeature } from "../../types";

interface Props {
    features: LocationRecordFeature[];
}

/** Renders a historical track as a polyline with clickable waypoints. */
export default function TrackLayer({ features }: Props) {
    if (features.length === 0) return null;

    const positions: [number, number][] = features.map((f) => [
        f.geometry.coordinates[1],
        f.geometry.coordinates[0],
    ]);

    return (
        <>
            <Polyline positions={positions} color="#F59E0B" weight={3} opacity={0.8} />
            {features.map((f) => (
                <CircleMarker
                    key={f.properties.id}
                    center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                    radius={4}
                    color="#F59E0B"
                    fillOpacity={1}
                >
                    <Popup>
                        <div className="text-xs space-y-1">
                            <p className="font-semibold">{new Date(f.properties.timestamp).toLocaleString()}</p>
                            {f.properties.speed !== null && <p>Speed: {f.properties.speed.toFixed(1)} km/h</p>}
                            {f.properties.heading !== null && <p>Heading: {f.properties.heading.toFixed(0)}°</p>}
                            {f.properties.battery !== null && <p>Battery: {f.properties.battery}%</p>}
                        </div>
                    </Popup>
                </CircleMarker>
            ))}
        </>
    );
}
