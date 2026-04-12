import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryClient } from "../lib/queryClient";
import type { Device, Asset, PaginatedResponse } from "../types";

const EMPTY = { asset: "", serial_number: "", is_active: true, api_key: "" };

export default function DevicesPage() {
  const [editing, setEditing] = useState<Device | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const { data, isPending } = useQuery({
    queryKey: ["devices"],
    queryFn: () =>
      api.get<PaginatedResponse<Device>>("/api/v1/devices/").then((r) => r.data),
  });
  const devices = data?.results ?? [];

  const { data: assetsData } = useQuery({
    queryKey: ["assets"],
    queryFn: () =>
      api.get<PaginatedResponse<Asset>>("/api/v1/assets/").then((r) => r.data),
  });
  const assets = assetsData?.results ?? [];
  const assetMap = new Map(assets.map((a) => [a.id, a.name]));

  const createMut = useMutation({
    mutationFn: (payload: typeof EMPTY) =>
      api.post("/api/v1/devices/", {
        asset: payload.asset,
        serial_number: payload.serial_number,
        is_active: payload.is_active,
        api_key: payload.api_key,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      setCreating(false);
      setForm(EMPTY);
    },
    onError: () => setError("Failed to create device. Check all fields and ensure serial number is unique."),
  });

  const updateMut = useMutation({
    mutationFn: (device: Device) => {
      const payload: Record<string, unknown> = {
        serial_number: form.serial_number,
        is_active: form.is_active,
        asset: form.asset,
      };
      if (form.api_key) payload.api_key = form.api_key;
      return api.patch(`/api/v1/devices/${device.id}/`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      setEditing(null);
    },
    onError: () => setError("Failed to update device."),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/devices/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
    onError: () => setError("Failed to delete device."),
  });

  const openEdit = (device: Device) => {
    setEditing(device);
    setForm({
      asset: device.asset,
      serial_number: device.serial_number,
      is_active: device.is_active,
      api_key: "",
    });
    setCreating(false);
    setError("");
  };

  const openCreate = () => {
    setCreating(true);
    setEditing(null);
    setForm({ ...EMPTY, asset: assets[0]?.id ?? "" });
    setError("");
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Devices</h1>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-bold">✕</button>
        </div>
      )}

      {(creating || editing) && (
        <div className="mb-6 rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            {creating ? "New Device" : `Edit: ${editing!.serial_number}`}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">Serial Number *</label>
              <input
                value={form.serial_number}
                onChange={(e) => setForm({ ...form, serial_number: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">Asset *</label>
              <select
                value={form.asset}
                onChange={(e) => setForm({ ...form, asset: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="">— select —</option>
                {assets.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">
                API Key {creating ? "*" : "(leave blank to keep existing)"}
              </label>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                placeholder={creating ? "Enter API key" : "New key (optional)"}
                autoComplete="new-password"
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                Active
              </label>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => creating ? createMut.mutate(form) : updateMut.mutate(editing!)}
              disabled={
                !form.serial_number || !form.asset ||
                (creating && !form.api_key) ||
                createMut.isPending || updateMut.isPending
              }
              className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Create" : "Save"}
            </button>
            <button
              onClick={() => { setCreating(false); setEditing(null); }}
              className="rounded border border-gray-300 px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isPending ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Serial Number</th>
                <th className="px-4 py-3 text-left">Asset</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {devices.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    No devices found.
                  </td>
                </tr>
              ) : (
                devices.map((device) => (
                  <tr key={device.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800 font-mono">
                      {device.serial_number}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {assetMap.get(device.asset) ?? device.asset}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          device.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {device.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(device.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => openEdit(device)} className="mr-2 text-xs text-blue-600 hover:underline">
                        Edit
                      </button>
                      <button
                        onClick={() => confirm("Delete this device?") && deleteMut.mutate(device.id)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
