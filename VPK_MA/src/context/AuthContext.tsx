import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { api, AppSession, setActiveSession } from '../api/client';

const SESSION_KEY = 'vpk_ma_session_v1';
const useSecure = Platform.OS === 'ios' || Platform.OS === 'android';

type AuthContextValue = {
  session: AppSession | null;
  loading: boolean;
  login: (login: string, password: string, db?: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function readStored() {
  if (useSecure) return SecureStore.getItemAsync(SESSION_KEY);
  return AsyncStorage.getItem(SESSION_KEY);
}

async function writeStored(value: string) {
  if (useSecure) return SecureStore.setItemAsync(SESSION_KEY, value);
  return AsyncStorage.setItem(SESSION_KEY, value);
}

async function removeStored() {
  if (useSecure) return SecureStore.deleteItemAsync(SESSION_KEY);
  return AsyncStorage.removeItem(SESSION_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AppSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const raw = await readStored();
        if (!raw) return;
        const parsed = JSON.parse(raw) as AppSession;
        if (!parsed.sessionId) return;
        setActiveSession(parsed);
        await api('/me');
        setSession(parsed);
      } catch {
        setActiveSession(null);
        await removeStored();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      loading,
      login: async (loginName, password, db) => {
        const data = await api<{ session_id: string; user: AppSession['user'] }>('/auth/login', {
          method: 'POST',
          body: { login: loginName, password, db },
        });
        const next = { sessionId: data.session_id, user: data.user };
        setActiveSession(next);
        await writeStored(JSON.stringify(next));
        setSession(next);
      },
      logout: async () => {
        try {
          await api('/auth/logout', { method: 'POST' });
        } catch {
          // session may already be gone
        }
        setActiveSession(null);
        await removeStored();
        setSession(null);
      },
    }),
    [session, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
