import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { queryClient } from "../lib/queryClient";
import type { Organization, PaginatedResponse } from "../types";

const EMPTY: Omit<Organization, "id" | "created_at"> = { name: "", slug: "" };

export default function OrgsPage() {
  const [editing, setEditing] = useState<Organization | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const { data, isPending } = useQuery({
    queryKey: ["organizations"],
    queryFn: () =>
      api.get<PaginatedResponse<Organization>>("/api/v1/organizations/").then((r) => r.data),
  });
  const orgs = data?.results ?? [];

  const createMut = useMutation({
    mutationFn: (payload: typeof EMPTY) => api.post("/api/v1/organizations/", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      setCreating(false);
      setForm(EMPTY);
    },
    onError: () => setError("Failed to create organization."),
  });

  const updateMut = useMutation({
    mutationFn: (org: Organization) =>
      api.patch(`/api/v1/organizations/${org.id}/`, { name: form.name, slug: form.slug }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      setEditing(null);
    },
    onError: () => setError("Failed to update organization."),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/organizations/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["organizations"] }),
    onError: () => setError("Failed to delete organization."),
  });

  const openEdit = (org: Organization) => {
    setEditing(org);
    setForm({ name: org.name, slug: org.slug });
    setCreating(false);
    setError("");
  };

  const openCreate = () => {
    setCreating(true);
    setEditing(null);
    setForm(EMPTY);
    setError("");
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-800">Organizations</h1>
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

      {/* Form panel */}
      {(creating || editing) && (
        <div className="mb-6 rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">
            {creating ? "New Organization" : `Edit: ${editing!.name}`}
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
              <label className="mb-0.5 block text-xs text-gray-500">Slug *</label>
              <input
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => (creating ? createMut.mutate(form) : updateMut.mutate(editing!))}
              disabled={!form.name || !form.slug || createMut.isPending || updateMut.isPending}
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

      {/* Table */}
      {isPending ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Slug</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {orgs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    No organizations found.
                  </td>
                </tr>
              ) : (
                orgs.map((org) => (
                  <tr key={org.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{org.name}</td>
                    <td className="px-4 py-3 text-gray-500">{org.slug}</td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => openEdit(org)}
                        className="mr-2 text-xs text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => confirm("Delete?") && deleteMut.mutate(org.id)}
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
