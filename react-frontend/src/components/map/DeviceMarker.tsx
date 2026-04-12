import L from "leaflet";
import type { LivePosition } from "../../types";

/** Create a rotated SVG arrow DivIcon for a device marker. */
export function createDeviceIcon(heading: number | null, isSelected = false): L.DivIcon {
    const deg = heading ?? 0;
    const color = isSelected ? "#F59E0B" : "#3B82F6";
    return L.divIcon({
        html: `<div style="transform:rotate(${deg}deg);width:28px;height:28px;display:flex;align-items:center;justify-content:center;">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="${color}" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L4.5 20.5L12 17L19.5 20.5Z"/>
      </svg>
    </div>`,
        className: "",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

/** Format a LivePosition's timestamp for display. */
export function formatTs(ts: string | null): string {
    if (!ts) return "—";
    try {
        return new Date(ts).toLocaleTimeString();
    } catch {
        return ts;
    }
}

/** Format a nullable numeric string from Redis for display. */
export function fmt(val: string | null, unit = "", decimals = 1): string {
    if (val === null || val === "") return "—";
    const n = parseFloat(val);
    return isNaN(n) ? "—" : `${n.toFixed(decimals)}${unit}`;
}

export type { LivePosition };
