import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { RootStackParamList } from '../../App';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type HomeData = {
  date_label: string;
  kpis: { key: string; label: string; value: string | number; foot: string; tone: string; money?: boolean; filter: string }[];
  alerts: { id: number; name: string; message: string; detail: string }[];
};

const PERIODS = [
  ['today', 'วันนี้'],
  ['7d', '7 วัน'],
  ['30d', '30 วัน'],
] as const;

export function HomeScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { session, logout } = useAuth();
  const [period, setPeriod] = useState<(typeof PERIODS)[number][0]>('today');
  const [data, setData] = useState<HomeData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api<HomeData & { ok: boolean }>(`/home?period=${period}`)
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, [period]);

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Text style={styles.kicker}>{data?.date_label || 'ติดตามงานซ่อม'}</Text>
      <View style={styles.titleRow}>
        <Text style={styles.title}>{session?.user.name}</Text>
        <Pressable onPress={logout}>
          <Text style={styles.link}>ออก</Text>
        </Pressable>
      </View>
      <View style={styles.actions}>
        <Pressable style={styles.action} onPress={() => navigation.navigate('NewRequest')}>
          <View style={styles.actionIcon}>
            <Text style={styles.actionGlyph}>+</Text>
          </View>
          <Text style={styles.actionLabel}>แจ้งซ่อม</Text>
        </Pressable>
      </View>
      <View style={styles.periods}>
        {PERIODS.map(([id, label]) => (
          <Pressable key={id} style={[styles.chip, period === id && styles.chipOn]} onPress={() => setPeriod(id)}>
            <Text style={[styles.chipText, period === id && styles.chipTextOn]}>{label}</Text>
          </Pressable>
        ))}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.grid}>
        {(data?.kpis || []).map((kpi) => (
          <Pressable
            key={kpi.key}
            style={styles.kpi}
            onPress={() => navigation.navigate('Jobs', { filter: kpi.filter, title: kpi.label })}
          >
            <Text style={styles.kpiLabel}>{kpi.label}</Text>
            <Text style={[styles.kpiValue, kpi.money && styles.kpiMoney, toneStyle(kpi.tone)]}>{kpi.value}</Text>
            <Text style={styles.kpiFoot}>{kpi.foot}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.section}>ต้องติดตาม</Text>
      {(data?.alerts || []).length === 0 ? <Text style={styles.empty}>ไม่มีรายการเร่ง</Text> : null}
      {(data?.alerts || []).map((alert) => (
        <Pressable key={`${alert.id}-${alert.message}`} style={styles.card} onPress={() => navigation.navigate('JobDetail', { id: alert.id })}>
          <Text style={styles.cardTitle}>{alert.name}</Text>
          <Text style={styles.cardMeta}>{alert.message} · {alert.detail}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

function toneStyle(tone: string) {
  if (tone === 'green') return { color: colors.success };
  if (tone === 'orange' || tone === 'alert') return { color: colors.warning };
  return { color: colors.brand };
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  kicker: { color: colors.muted, fontFamily: fonts.regular },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 },
  title: { fontSize: 24, fontFamily: fonts.bold, color: colors.ink },
  link: { color: colors.brand, fontFamily: fonts.semiBold },
  actions: { flexDirection: 'row', marginTop: 16 },
  action: { alignItems: 'center', width: 76 },
  actionIcon: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionGlyph: { color: '#fff', fontSize: 32, lineHeight: 36, fontFamily: fonts.bold },
  actionLabel: { marginTop: 6, fontFamily: fonts.medium, color: colors.ink, fontSize: 13 },
  periods: { flexDirection: 'row', gap: 8, marginTop: 14 },
  chip: { borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line },
  chipOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  chipText: { fontFamily: fonts.medium, color: colors.ink },
  chipTextOn: { color: '#fff' },
  error: { color: colors.danger, marginTop: 12, fontFamily: fonts.regular },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 14 },
  kpi: { width: '48%', backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1, borderColor: colors.line, padding: 12 },
  kpiLabel: { color: colors.muted, fontFamily: fonts.regular, fontSize: 12 },
  kpiValue: { marginTop: 6, fontSize: 26, fontFamily: fonts.bold },
  kpiMoney: { fontSize: 18 },
  kpiFoot: { marginTop: 4, color: colors.muted, fontFamily: fonts.regular, fontSize: 12 },
  section: { marginTop: 18, marginBottom: 8, fontFamily: fonts.semiBold, fontSize: 16, color: colors.ink },
  empty: { color: colors.muted, fontFamily: fonts.regular },
  card: { backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1, borderColor: colors.line, padding: 12, marginBottom: 8 },
  cardTitle: { fontFamily: fonts.semiBold, color: colors.ink },
  cardMeta: { marginTop: 4, color: colors.muted, fontFamily: fonts.regular },
});
