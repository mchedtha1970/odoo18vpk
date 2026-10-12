import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  applyOdooServerId,
  ODOO_CONFIG,
  ODOO_SERVERS,
  type OdooServerId,
} from '../config/odoo';
import { useAuth } from '../context/AuthContext';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

const LAST_SERVER_KEY = 'vpk_ma_last_server_v1';

type SavedServer = { id: OdooServerId; customUrl?: string; db?: string };

export function LoginScreen() {
  const { login } = useAuth();
  const [serverId, setServerId] = useState<OdooServerId>('docker');
  const [customUrl, setCustomUrl] = useState('http://127.0.0.1:8069');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [db, setDb] = useState(ODOO_CONFIG.defaultDb);
  const [showDb, setShowDb] = useState(false);
  const [showExtra, setShowExtra] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(LAST_SERVER_KEY);
        if (!raw) {
          applyOdooServerId('docker');
          return;
        }
        const saved = JSON.parse(raw) as SavedServer;
        if (saved.id === 'docker' || saved.id === 'uat' || saved.id === 'custom') {
          setServerId(saved.id);
          if (saved.customUrl) setCustomUrl(saved.customUrl);
          applyOdooServerId(saved.id, saved.customUrl);
          setDb(saved.db || ODOO_CONFIG.defaultDb);
          if (saved.id !== 'docker') setShowExtra(true);
        }
      } catch {
        applyOdooServerId('docker');
      }
    })();
  }, []);

  const selectServer = (id: OdooServerId) => {
    setServerId(id);
    applyOdooServerId(id, customUrl);
    setDb(ODOO_CONFIG.defaultDb);
    setError(null);
  };

  const canSubmit = useMemo(
    () => username.trim().length > 0 && password.length > 0 && !submitting,
    [username, password, submitting],
  );

  const onSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      applyOdooServerId(serverId, customUrl);
      await AsyncStorage.setItem(
        LAST_SERVER_KEY,
        JSON.stringify({ id: serverId, customUrl, db } satisfies SavedServer),
      );
      await login(username.trim(), password, db);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'เข้าสู่ระบบไม่สำเร็จ');
    } finally {
      setSubmitting(false);
    }
  };

  const hostLabel =
    serverId === 'custom'
      ? customUrl.replace(/^https?:\/\//, '')
      : ODOO_SERVERS[serverId === 'uat' ? 'uat' : 'docker'].host;

  return (
    <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.hero}>
        <View style={styles.logoMark}>
          <Text style={styles.logoGlyph}>✓</Text>
        </View>
        <Text style={styles.brand}>ซ่อมบำรุง</Text>
        <Text style={styles.subtitle}>เข้าสู่ระบบ Odoo สำหรับงานซ่อมบำรุง</Text>
        <Text style={styles.host}>{hostLabel}</Text>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Username / Email</Text>
        <TextInput
          style={styles.input}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          placeholder="user@company.com"
          placeholderTextColor={colors.muted}
          value={username}
          onChangeText={setUsername}
        />
        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          secureTextEntry
          placeholder="••••••••"
          placeholderTextColor={colors.muted}
          value={password}
          onChangeText={setPassword}
          onSubmitEditing={onSubmit}
        />
        <Pressable onPress={() => setShowExtra((value) => !value)} style={styles.dbToggle}>
          <Text style={styles.dbToggleText}>ข้อมูลเพิ่มเติม {showExtra ? '▴' : '▾'}</Text>
        </Pressable>
        {showExtra ? (
          <View style={styles.extraBox}>
            <Text style={styles.label}>เซิร์ฟเวอร์</Text>
            <View style={styles.serverRow}>
              {(
                [
                  ['docker', 'Local Docker'],
                  ['uat', 'UAT'],
                  ['custom', 'URL'],
                ] as const
              ).map(([id, label]) => (
                <Pressable
                  key={id}
                  style={[styles.serverChip, serverId === id && styles.serverChipActive]}
                  onPress={() => selectServer(id)}
                >
                  <Text style={[styles.serverChipText, serverId === id && styles.serverChipTextActive]}>
                    {label}
                  </Text>
                </Pressable>
              ))}
            </View>
            {serverId === 'docker' ? (
              <Text style={styles.hint}>
                เชื่อมต่อ Odoo Docker ที่ http://127.0.0.1:8069 (DB: VPK-S1)
                {'\n'}ใช้ได้กับ iOS Simulator บนเครื่องนี้
              </Text>
            ) : null}
            {serverId === 'custom' ? (
              <>
                <Text style={styles.label}>Base URL</Text>
                <TextInput
                  style={styles.input}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="http://127.0.0.1:8069"
                  placeholderTextColor={colors.muted}
                  value={customUrl}
                  onChangeText={(value) => {
                    setCustomUrl(value);
                    applyOdooServerId('custom', value);
                  }}
                />
              </>
            ) : null}
            <Pressable onPress={() => setShowDb((value) => !value)} style={styles.dbToggle}>
              <Text style={styles.dbToggleText}>
                Database: {db} {showDb ? '▴' : '▾'}
              </Text>
            </Pressable>
            {showDb
              ? ODOO_CONFIG.databases.map((name) => (
                  <Pressable
                    key={name}
                    onPress={() => {
                      setDb(name);
                      setShowDb(false);
                    }}
                    style={[styles.dbItem, db === name && styles.dbItemActive]}
                  >
                    <Text style={[styles.dbItemText, db === name && styles.dbItemTextActive]}>{name}</Text>
                  </Pressable>
                ))
              : null}
          </View>
        ) : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable style={[styles.button, !canSubmit && styles.buttonDisabled]} disabled={!canSubmit} onPress={onSubmit}>
          {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>เข้าสู่ระบบ</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg, paddingHorizontal: 24, justifyContent: 'center' },
  hero: { marginBottom: 28 },
  logoMark: {
    width: 64,
    height: 64,
    borderRadius: 18,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  logoGlyph: { color: '#fff', fontSize: 32, fontFamily: fonts.bold },
  brand: { fontSize: 32, fontFamily: fonts.bold, color: colors.ink, letterSpacing: -0.5 },
  subtitle: { marginTop: 8, fontSize: 15, lineHeight: 24, color: colors.muted, fontFamily: fonts.regular },
  host: { marginTop: 10, fontSize: 13, color: colors.brand, fontFamily: fonts.semiBold },
  form: { backgroundColor: colors.surface, borderRadius: 20, padding: 20, borderWidth: 1, borderColor: colors.line },
  label: { fontSize: 13, fontFamily: fonts.semiBold, color: colors.muted, marginBottom: 6, marginTop: 10 },
  input: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === 'ios' ? 14 : 10,
    fontSize: 16,
    color: colors.ink,
    backgroundColor: '#FAFCFB',
    fontFamily: fonts.regular,
  },
  dbToggle: { marginTop: 14, alignSelf: 'flex-start' },
  extraBox: { marginTop: 8, paddingTop: 4 },
  serverRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  serverChip: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.line,
  },
  serverChipActive: { backgroundColor: colors.brand, borderColor: colors.brand },
  serverChipText: { fontFamily: fonts.semiBold, fontSize: 12, color: colors.ink },
  serverChipTextActive: { color: '#fff' },
  hint: { marginTop: 6, marginBottom: 8, fontSize: 12, lineHeight: 18, color: colors.muted, fontFamily: fonts.regular },
  dbToggleText: { color: colors.brand, fontFamily: fonts.semiBold, fontSize: 13 },
  dbItem: { marginTop: 8, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10, backgroundColor: colors.bg },
  dbItemActive: { backgroundColor: '#D7EDEB' },
  dbItemText: { color: colors.ink, fontSize: 14, fontFamily: fonts.regular },
  dbItemTextActive: { fontFamily: fonts.bold, color: colors.brandDark },
  error: { marginTop: 14, color: colors.danger, fontSize: 14, fontFamily: fonts.medium },
  button: { marginTop: 18, backgroundColor: colors.brand, borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontSize: 16, fontFamily: fonts.bold },
});
