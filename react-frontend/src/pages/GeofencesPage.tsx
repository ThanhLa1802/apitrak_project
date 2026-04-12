import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { queryClient } from "../lib/queryClient";
import GeofenceMap from "../components/geofences/GeofenceMap";
import type { GeofenceFeature, GeofenceFeatureCollection } from "../types";

export default function GeofencesPage() {
    const { orgId } = useAuthStore();
    const [selected, setSelected] = useState<GeofenceFeature | null>(null);
    const [editName, setEditName] = useState("");
    const [editActive, setEditActive] = useState(true);

    const { data, isPending } = useQuery({
        queryKey: ["geofences", orgId],
        queryFn: () =>
            api
                .get<GeofenceFeatureCollection>(`/api/v1/geofences/?org_id=${orgId}`)
                .then((r) => r.data),
        enabled: !!orgId,
    });
    const geofences = data?.features ?? [];

    const createMutation = useMutation({
        mutationFn: (payload: { name: string; polygon: GeoJSON.MultiPolygon; organization: string }) =>
            api.post<GeofenceFeature>("/api/v1/geofences/", {
                type: "Feature",
                geometry: payload.polygon,
                properties: {
                    name: payload.name,
                    organization: payload.organization,
                    is_active: true,
                },
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["geofences", orgId] }),
    });

    const updateMutation = useMutation({
        mutationFn: (f: GeofenceFeature) =>
            api.patch(`/api/v1/geofences/${f.properties.id}/`, {
                type: "Feature",
                geometry: f.geometry,
                properties: { name: editName, is_active: editActive },
            }),
        onSuccess: () => {
            setSelected(null);
            queryClient.invalidateQueries({ queryKey: ["geofences", orgId] });
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.delete(`/api/v1/geofences/${id}/`),
        onSuccess: () => {
            setSelected(null);
            queryClient.invalidateQueries({ queryKey: ["geofences", orgId] });
        },
    });

    const handleCreated = (name: string, multipolygon: GeoJSON.MultiPolygon) => {
        if (!orgId) return;
        createMutation.mutate({ name, polygon: multipolygon, organization: orgId });
    };

    const handleDeleted = (id: string) => {
        if (confirm("Delete this geofence?")) deleteMutation.mutate(id);
    };

    const openEdit = (f: GeofenceFeature) => {
        setSelected(f);
        setEditName(f.properties.name);
        setEditActive(f.properties.is_active);
    };

    return (
        <div className="flex h-full">
            {/* Sidebar list */}
            <div className="flex w-72 flex-shrink-0 flex-col border-r bg-white">
                <div className="border-b px-4 py-3">
                    <h1 className="text-lg font-semibold text-gray-800">Geofences</h1>
                    <p className="text-xs text-gray-500">
                        Draw polygons on the map to create geofences.
                    </p>
                </div>

                {isPending ? (
                    <p className="p-4 text-sm text-gray-400">Loading…</p>
                ) : (
                    <ul className="flex-1 overflow-y-auto divide-y">
                        {geofences.length === 0 ? (
                            <li className="p-4 text-center text-sm text-gray-400">
                                No geofences yet. Draw a polygon on the map.
                            </li>
                        ) : (
                            geofences.map((f) => (
                                <li
                                    key={f.properties.id}
                                    className={`group flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-gray-50 ${selected?.properties.id === f.properties.id ? "bg-purple-50" : ""
                                        }`}
                                    onClick={() => openEdit(f)}
                                >
                                    <span className="h-3 w-3 rounded-full border-2 border-purple-500 bg-purple-100" />
                                    <div className="flex-1 min-w-0">
                                        <p className="truncate text-sm font-medium text-gray-800">
                                            {f.properties.name}
                                        </p>
                                        <p className={`text-xs ${f.properties.is_active ? "text-green-600" : "text-gray-400"}`}>
                                            {f.properties.is_active ? "Active" : "Inactive"}
                                        </p>
                                    </div>
                                </li>
                            ))
                        )}
                    </ul>
                )}

                {/* Edit panel */}
                {selected && (
                    <div className="border-t bg-gray-50 p-4 space-y-3">
                        <h3 className="text-sm font-semibold text-gray-700">Edit Geofence</h3>
                        <div>
                            <label className="mb-0.5 block text-xs text-gray-500">Name</label>
                            <input
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                            />
                        </div>
                        <label className="flex items-center gap-2 text-sm">
                            <input
                                type="checkbox"
                                checked={editActive}
                                onChange={(e) => setEditActive(e.target.checked)}
                            />
                            Active
                        </label>
                        <div className="flex gap-2">
                            <button
                                onClick={() => selected && updateMutation.mutate(selected)}
                                disabled={updateMutation.isPending}
                                className="flex-1 rounded bg-blue-600 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                                Save
                            </button>
                            <button
                                onClick={() => deleteMutation.mutate(selected.properties.id)}
                                disabled={deleteMutation.isPending}
                                className="rounded border border-red-300 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                            >
                                Delete
                            </button>
                            <button
                                onClick={() => setSelected(null)}
                                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Map */}
            <div className="flex-1">
                <GeofenceMap
                    geofences={geofences}
                    onCreated={handleCreated}
                    onDeleted={handleDeleted}
                />
            </div>
        </div>
    );
}
