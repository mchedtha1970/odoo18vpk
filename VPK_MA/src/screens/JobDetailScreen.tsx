import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api } from '../api/client';
import type { RootStackParamList } from '../../App';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Detail = {
  name: string;
  receipt_number: string;
  status: string;
  sub_state: string;
  team: string;
  department: string;
  request_date: string;
  symptom: string;
  equipment: string;
  machine_number: string;
  requester: string;
  phone: string;
  repair_detail: string;
  parts: { id: number; name: string; qty: number }[];
  states: { key: string; label: string }[];
};

export function JobDetailScreen({ route }: NativeStackScreenProps<RootStackParamList, 'JobDetail'>) {
  const [record, setRecord] = useState<Detail | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ request: Detail }>(`/requests/${route.params.id}`)
      .then((data) => {
        setRecord(data.request);
        setNote(data.request.repair_detail || '');
      })
      .catch((err: Error) => setError(err.message));
  }, [route.params.id]);

  async function save(subState: string) {
    setBusy(true);
    setError('');
    try {
      const data = await api<{ request: Detail }>(`/requests/${route.params.id}`, {
        method: 'POST',
        body: { sub_state: subState, repair_detail: note },
      });
      setRecord(data.request);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'บันทึกไม่สำเร็จ');
    } finally {
      setBusy(false);
    }
  }

  if (!record) {
    return (
      <View style={styles.root}>
        <Text style={styles.meta}>{error || 'กำลังโหลด...'}</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Text style={styles.title}>{record.name}</Text>
      <Text style={styles.meta}>{[record.status, record.team, record.department, record.request_date].filter(Boolean).join(' · ')}</Text>
      <View style={styles.block}>
        <Text style={styles.heading}>อาการชำรุด</Text>
        <Text style={styles.body}>{record.symptom || '-'}</Text>
        <Text style={styles.meta}>
          {[record.equipment, record.machine_number && `เครื่อง ${record.machine_number}`, record.requester, record.phone]
            .filter(Boolean)
            .join(' · ')}
        </Text>
      </View>
      <View style={styles.block}>
        <Text style={styles.heading}>อะไหล่ที่เบิก</Text>
        {record.parts.length === 0 ? <Text style={styles.meta}>ยังไม่มีการเบิก</Text> : null}
        {record.parts.map((part) => (
          <Text key={part.id} style={styles.body}>{part.name} · {part.qty}</Text>
        ))}
      </View>
      <View style={styles.block}>
        <Text style={styles.heading}>สถานะและรายละเอียดการซ่อม</Text>
        <View style={styles.states}>
          {record.states.map((state) => (
            <Pressable
              key={state.key}
              disabled={busy}
              style={[styles.chip, record.sub_state === state.key && styles.chipOn]}
              onPress={() => save(state.key)}
            >
              <Text style={[styles.chipText, record.sub_state === state.key && styles.chipTextOn]}>{state.label}</Text>
            </Pressable>
          ))}
        </View>
        <TextInput style={styles.note} multiline value={note} onChangeText={setNote} />
        <Pressable style={styles.button} disabled={busy} onPress={() => save(record.sub_state)}>
          <Text style={styles.buttonText}>บันทึกรายละเอียด</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 32 },
  title: { fontSize: 22, fontFamily: fonts.bold, color: colors.ink },
  meta: { marginTop: 6, color: colors.muted, fontFamily: fonts.regular },
  error: { color: colors.danger, marginBottom: 8, fontFamily: fonts.regular },
  block: { marginTop: 12, backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1, borderColor: colors.line, padding: 12 },
  heading: { fontFamily: fonts.semiBold, color: colors.ink, marginBottom: 6 },
  body: { fontFamily: fonts.regular, color: colors.ink, lineHeight: 22 },
  states: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.bg, borderWidth: 1, borderColor: colors.line },
  chipOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  chipText: { fontFamily: fonts.medium, color: colors.ink },
  chipTextOn: { color: '#fff' },
  note: {
    marginTop: 12,
    minHeight: 88,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 10,
    fontFamily: fonts.regular,
    color: colors.ink,
    textAlignVertical: 'top',
  },
  button: { marginTop: 12, backgroundColor: colors.brand, borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontFamily: fonts.bold },
});
