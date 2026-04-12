// ── Organizations ─────────────────────────────────────────────────────────────

export interface Organization {
    id: string;
    name: string;
    slug: string;
    created_at: string;
}

// ── Assets ────────────────────────────────────────────────────────────────────

export type AssetType = "vehicle" | "container" | "person" | "equipment" | "other";

export interface Asset {
    id: string;
    organization: string;
    name: string;
    asset_type: AssetType;
    is_active: boolean;
    created_at: string;
}

// ── Devices ───────────────────────────────────────────────────────────────────

export interface Device {
    id: string;
    asset: string;
    serial_number: string;
    is_active: boolean;
    created_at: string;
}

export interface DeviceWrite extends Omit<Device, "id" | "created_at"> {
    api_key?: string;
}

// ── Geofences ────────────────────────────────────────────────────────────────

export interface GeofenceProperties {
    id: string;
    organization: string;
    name: string;
    is_active: boolean;
    created_at: string;
}

export interface GeofenceFeature {
    type: "Feature";
    geometry: GeoJSON.MultiPolygon;
    properties: GeofenceProperties;
}

export interface GeofenceFeatureCollection {
    type: "FeatureCollection";
    features: GeofenceFeature[];
}

// ── Tracking ─────────────────────────────────────────────────────────────────

export interface LivePosition {
    device_id: string;
    lat: string;
    lng: string;
    ts: string;
    speed: string | null;
    heading: string | null;
    accuracy: string | null;
    battery: string | null;
}

export interface LiveMapResponse {
    org_id: string;
    devices: LivePosition[];
}

export interface LocationRecordProperties {
    id: string;
    device: string;
    timestamp: string;
    speed: number | null;
    heading: number | null;
    accuracy: number | null;
    battery: number | null;
}

export interface LocationRecordFeature {
    type: "Feature";
    geometry: GeoJSON.Point;
    properties: LocationRecordProperties;
}

export interface TrackResponse {
    type: "FeatureCollection";
    next: string | null;
    previous: string | null;
    features: LocationRecordFeature[];
    count: number;
}

// ── WebSocket messages ────────────────────────────────────────────────────────

export interface WsLocationUpdate {
    type: "location_update";
    device_id: string;
    lat: string;
    lng: string;
    timestamp: string;
    speed: string | null;
    heading: string | null;
    battery: string | null;
}

export interface WsGeofenceEvent {
    type: "geofence_event";
    event: "entered" | "exited";
    device_id: string;
    geofence_id: string;
}

export type WsMessage = WsLocationUpdate | WsGeofenceEvent;

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthTokens {
    access: string;
    refresh: string;
}

export interface OrgScopeTokenResponse {
    token: string;
    org_id: string;
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}
