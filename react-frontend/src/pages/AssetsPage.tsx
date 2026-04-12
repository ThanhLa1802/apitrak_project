import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryClient } from "../lib/queryClient";
import type { Asset, AssetType, Organization, PaginatedResponse } from "../types";

const ASSET_TYPES: AssetType[] = ["vehicle", "container", "person", "equipment", "other"];

const EMPTY = { organization: "", name: "", asset_type: "vehicle" as AssetType, is_active: true };

export default function AssetsPage() {
  const [editing, setEditing] = useState<Asset | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const { data, isPending } = useQuery({
    queryKey: ["assets"],
    queryFn: () =>
      api.get<PaginatedResponse<Asset>>("/api/v1/assets/").then((r) => r.data),
  });
  const assets = data?.results ?? [];

  const { data: orgsData } = useQuery({
    queryKey: ["organizations"],
    queryFn: () =>
      api.get<PaginatedResponse<Organization>>("/api/v1/organizations/").then((r) => r.data),
  });
  const orgs = orgsData?.results ?? [];
  const orgMap = new Map(orgs.map((o) => [o.id, o.name]));

  const createMut = useMutation({
    mutationFn: (payload: typeof EMPTY) => api.post("/api/v1/assets/", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setCreating(false);
      setForm(EMPTY);
    },
    onError: () => setError("Failed to create asset."),
  });

  const updateMut = useMutation({
    mutationFn: (asset: Asset) =>
      api.patch(`/api/v1/assets/${asset.id}/`, {
        name: form.name,
        asset_type: form.asset_type,
        is_active: form.is_active,
        organization: form.organization,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
    },
    onError: () => setError("Failed to update asset."),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/assets/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
    onError: () => setError("Failed to delete asset."),
  });

  const openEdit = (asset: Asset) => {
    setEditing(asset);
    setForm({
      organization: asset.organization,
      name: asset.name,
      asset_type: asset.asset_type,
      is_active: asset.is_active,
    });
    setCreating(false);
    setError("");
  };

  const openCreate = () => {
    setCreating(true);
    setEditing(null);
    setForm({ ...EMPTY, organization: orgs[0]?.id ?? "" });
    setError("");
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Assets</h1>
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
            {creating ? "New Asset" : `Edit: ${editing!.name}`}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">Name *</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">Organization *</label>
              <select
                value={form.organization}
                onChange={(e) => setForm({ ...form, organization: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="">— select —</option>
                {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-0.5 block text-xs text-gray-500">Type</label>
              <select
                value={form.asset_type}
                onChange={(e) => setForm({ ...form, asset_type: e.target.value as AssetType })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                {ASSET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
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
              disabled={!form.name || !form.organization || createMut.isPending || updateMut.isPending}
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
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Organization</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {assets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    No assets found.
                  </td>
                </tr>
              ) : (
                assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{asset.name}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {orgMap.get(asset.organization) ?? asset.organization}
                    </td>
                    <td className="px-4 py-3 capitalize text-gray-500">{asset.asset_type}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          asset.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {asset.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => openEdit(asset)} className="mr-2 text-xs text-blue-600 hover:underline">
                        Edit
                      </button>
                      <button
                        onClick={() => confirm("Delete this asset?") && deleteMut.mutate(asset.id)}
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
