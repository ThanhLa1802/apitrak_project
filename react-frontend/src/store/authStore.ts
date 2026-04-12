import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
    accessToken: string | null;
    refreshToken: string | null;
    /** Short-lived HS256 JWT with org_id claim — used for WebSocket connections */
    orgToken: string | null;
    orgId: string | null;
    orgName: string | null;

    setTokens: (access: string, refresh: string) => void;
    setOrgContext: (orgId: string, orgName: string, orgToken: string) => void;
    clearOrgContext: () => void;
    logout: () => void;
    isAuthenticated: () => boolean;
    hasOrgContext: () => boolean;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            accessToken: null,
            refreshToken: null,
            orgToken: null,
            orgId: null,
            orgName: null,

            setTokens: (access, refresh) =>
                set({ accessToken: access, refreshToken: refresh }),

            setOrgContext: (orgId, orgName, orgToken) =>
                set({ orgId, orgName, orgToken }),

            clearOrgContext: () =>
                set({ orgId: null, orgName: null, orgToken: null }),

            logout: () =>
                set({
                    accessToken: null,
                    refreshToken: null,
                    orgToken: null,
                    orgId: null,
                    orgName: null,
                }),

            isAuthenticated: () => get().accessToken !== null,
            hasOrgContext: () => get().orgId !== null && get().orgToken !== null,
        }),
        {
            name: "apitrak-auth",
            partialize: (state) => ({
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
                orgToken: state.orgToken,
                orgId: state.orgId,
                orgName: state.orgName,
            }),
        },
    ),
);
