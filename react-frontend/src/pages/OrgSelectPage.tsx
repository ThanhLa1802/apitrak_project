import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import type { Organization, PaginatedResponse, OrgScopeTokenResponse } from "../types";

export default function OrgSelectPage() {
    const { setOrgContext, logout } = useAuthStore();
    const navigate = useNavigate();

    const { data, isPending, isError } = useQuery({
        queryKey: ["organizations"],
        queryFn: () =>
            api
                .get<PaginatedResponse<Organization>>("/api/v1/organizations/")
                .then((r) => r.data),
    });

    const handleSelect = async (org: Organization) => {
        try {
            const { data: scopeData } = await api.post<OrgScopeTokenResponse>(
                "/api/v1/token/org-scope/",
                { org_id: org.id },
            );
            setOrgContext(org.id, org.name, scopeData.token);
            navigate("/map");
        } catch {
            alert("Failed to create org-scoped token. Please try again.");
        }
    };

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    if (isPending) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-900 text-white">
                Loading organizations…
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-900 text-white">
                <p>Failed to load organizations.</p>
                <button onClick={handleLogout} className="text-sm text-blue-400 underline">
                    Log out and try again
                </button>
            </div>
        );
    }

    const orgs = data?.results ?? [];

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-900">
            <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
                <h1 className="mb-2 text-xl font-bold text-gray-800">Select Organization</h1>
                <p className="mb-6 text-sm text-gray-500">Choose the organization to work with.</p>

                {orgs.length === 0 ? (
                    <p className="text-sm text-gray-500">No organizations found.</p>
                ) : (
                    <ul className="divide-y divide-gray-200">
                        {orgs.map((org) => (
                            <li key={org.id}>
                                <button
                                    onClick={() => handleSelect(org)}
                                    className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-blue-50"
                                >
                                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                                        {org.name[0]?.toUpperCase()}
                                    </span>
                                    <div>
                                        <p className="text-sm font-medium text-gray-800">{org.name}</p>
                                        <p className="text-xs text-gray-400">{org.slug}</p>
                                    </div>
                                </button>
                            </li>
                        ))}
                    </ul>
                )}

                <button
                    onClick={handleLogout}
                    className="mt-6 text-sm text-gray-400 underline"
                >
                    Log out
                </button>
            </div>
        </div>
    );
}
