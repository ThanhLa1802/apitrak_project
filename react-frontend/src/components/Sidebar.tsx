import { NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { queryClient } from "../lib/queryClient";

const NAV_LINKS = [
    { to: "/map", label: "Live Map" },
    { to: "/geofences", label: "Geofences" },
    { to: "/assets", label: "Assets" },
    { to: "/devices", label: "Devices" },
    { to: "/organizations", label: "Organizations" },
];

export default function Sidebar() {
    const { orgName, logout, clearOrgContext } = useAuthStore();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        queryClient.clear();
        navigate("/login");
    };

    const handleSwitchOrg = () => {
        clearOrgContext();
        queryClient.clear();
        navigate("/org-select");
    };

    return (
        <aside className="flex w-56 flex-col bg-gray-900 text-white">
            <div className="px-4 py-5">
                <span className="text-xl font-bold tracking-wide text-blue-400">ApiTrak</span>
                {orgName && (
                    <button
                        onClick={handleSwitchOrg}
                        className="mt-1 block w-full truncate text-left text-xs text-gray-400 hover:text-gray-200"
                        title="Switch organization"
                    >
                        {orgName}
                    </button>
                )}
            </div>

            <nav className="flex-1 space-y-1 px-2 pb-4">
                {NAV_LINKS.map(({ to, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `block rounded px-3 py-2 text-sm font-medium transition-colors ${isActive
                                ? "bg-blue-600 text-white"
                                : "text-gray-300 hover:bg-gray-700 hover:text-white"
                            }`
                        }
                    >
                        {label}
                    </NavLink>
                ))}
            </nav>

            <div className="border-t border-gray-700 p-4">
                <button
                    onClick={handleLogout}
                    className="block w-full rounded px-3 py-2 text-left text-sm text-gray-400 hover:bg-gray-700 hover:text-white"
                >
                    Log out
                </button>
            </div>
        </aside>
    );
}
