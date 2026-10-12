import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api } from '../api/client';
import type { RootStackParamList } from '../../App';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

const FILTERS: Record<string, string> = {
  open: 'งานค้าง',
  waiting_assessment: 'รอประเมิน',
  assessed: 'ประเมินแล้ว',
  repairing: 'กำลังซ่อม',
  waiting_parts: 'รออะไหล่',
  waiting_disposal: 'รอจำหน่าย',
  repaired: 'ซ่อมเสร็จ',
  with_parts: 'เบิกอะไหล่แล้ว',
  all: 'ทั้งหมด',
};

type Job = {
  id: number;
  name: string;
  receipt_number: string;
  status: string;
  team: string;
  request_date: string;
};

export function JobsScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'Jobs'>) {
  const [filter, setFilter] = useState(route.params?.filter || 'open');
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<Job[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const handle = setTimeout(() => {
      const params = new URLSearchParams({ state: filter, q: query });
      api<{ requests: Job[] }>(`/requests?${params}`)
        .then((data) => {
          setRows(data.requests || []);
          setError('');
        })
        .catch((err: Error) => setError(err.message));
    }, 200);
    return () => clearTimeout(handle);
  }, [filter, query]);

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <TextInput
        style={styles.search}
        placeholder="ค้นหาเรื่อง เลขที่ หรือครุภัณฑ์"
        placeholderTextColor={colors.muted}
        value={query}
        onChangeText={setQuery}
      />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
        {Object.entries(FILTERS).map(([id, label]) => (
          <Pressable key={id} style={[styles.chip, filter === id && styles.chipOn]} onPress={() => setFilter(id)}>
            <Text style={[styles.chipText, filter === id && styles.chipTextOn]}>{label}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {rows.length === 0 && !error ? <Text style={styles.empty}>ไม่พบใบงาน</Text> : null}
      {rows.map((row) => (
        <Pressable key={row.id} style={styles.card} onPress={() => navigation.navigate('JobDetail', { id: row.id })}>
          <Text style={styles.title}>{row.name}</Text>
          <Text style={styles.meta}>{[row.receipt_number, row.status, row.team, row.request_date].filter(Boolean).join(' · ')}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  search: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontFamily: fonts.regular,
    color: colors.ink,
  },
  filters: { gap: 8, paddingVertical: 12 },
  chip: { borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line },
  chipOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  chipText: { fontFamily: fonts.medium, color: colors.ink },
  chipTextOn: { color: '#fff' },
  error: { color: colors.danger, fontFamily: fonts.regular },
  empty: { color: colors.muted, textAlign: 'center', marginTop: 24, fontFamily: fonts.regular },
  card: { backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1, borderColor: colors.line, padding: 12, marginBottom: 8 },
  title: { fontFamily: fonts.semiBold, color: colors.ink },
  meta: { marginTop: 4, color: colors.muted, fontFamily: fonts.regular },
});
