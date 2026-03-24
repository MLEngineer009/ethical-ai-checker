import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "../services/api";

interface AuthUser {
  token: string;
  name: string;
  picture: string;
  isGuest: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  signIn: (user: AuthUser) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  signIn: () => {},
  signOut: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    restoreSession();
  }, []);

  const restoreSession = async () => {
    try {
      const stored = await AsyncStorage.getItem("auth_user");
      if (!stored) { setIsLoading(false); return; }
      const parsed: AuthUser = JSON.parse(stored);
      if (parsed.isGuest) { setIsLoading(false); return; } // guests don't persist
      // Validate token
      await api.me(parsed.token);
      setUser(parsed);
    } catch {
      await AsyncStorage.removeItem("auth_user");
    } finally {
      setIsLoading(false);
    }
  };

  const signIn = async (u: AuthUser) => {
    setUser(u);
    if (!u.isGuest) await AsyncStorage.setItem("auth_user", JSON.stringify(u));
  };

  const signOut = async () => {
    if (user?.token) await api.logout(user.token).catch(() => {});
    await AsyncStorage.removeItem("auth_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
