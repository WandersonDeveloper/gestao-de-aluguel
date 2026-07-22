import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, TOKEN_STORAGE_KEY, getApiErrorMessage } from "@/services/api";

export type UserRole = "admin" | "operador" | "financeiro";

export interface CurrentUser {
  id: number;
  nome: string;
  email: string;
  papel: UserRole;
  ativo: boolean;
}

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const response = await api.get<CurrentUser>("/users/me");
      setUser(response.data);
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  useEffect(() => {
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    try {
      const response = await api.post<{ access_token: string }>("/auth/login", { email, senha });
      localStorage.setItem(TOKEN_STORAGE_KEY, response.data.access_token);
    } catch (error) {
      throw new Error(getApiErrorMessage(error, "Não foi possível entrar."));
    }
    const me = await api.get<CurrentUser>("/users/me");
    setUser(me.data);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth precisa ser usado dentro de um AuthProvider");
  }
  return context;
}
