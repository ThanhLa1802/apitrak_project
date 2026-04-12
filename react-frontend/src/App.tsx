import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import OrgSelectPage from "./pages/OrgSelectPage";
import MapPage from "./pages/MapPage";
import GeofencesPage from "./pages/GeofencesPage";
import AssetsPage from "./pages/AssetsPage";
import DevicesPage from "./pages/DevicesPage";
import OrgsPage from "./pages/OrgsPage";

export default function App() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

    return (
        <Routes>
            <Route
                path="/login"
                element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
            />

            <Route element={<ProtectedRoute />}>
                <Route path="/org-select" element={<OrgSelectPage />} />

                <Route element={<ProtectedRoute requireOrg />}>
                    <Route element={<Layout />}>
                        <Route path="/" element={<Navigate to="/map" replace />} />
                        <Route path="/map" element={<MapPage />} />
                        <Route path="/geofences" element={<GeofencesPage />} />
                        <Route path="/assets" element={<AssetsPage />} />
                        <Route path="/devices" element={<DevicesPage />} />
                        <Route path="/organizations" element={<OrgsPage />} />
                    </Route>
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
