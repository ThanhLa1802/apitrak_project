import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

interface Props {
    requireOrg?: boolean;
}

export default function ProtectedRoute({ requireOrg = false }: Props) {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
    const hasOrgContext = useAuthStore((s) => s.hasOrgContext());

    if (!isAuthenticated) return <Navigate to="/login" replace />;
    if (requireOrg && !hasOrgContext) return <Navigate to="/org-select" replace />;

    return <Outlet />;
}
