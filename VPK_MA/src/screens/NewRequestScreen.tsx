import React, { useEffect, useRef, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { api } from '../api/client';
import type { RootStackParamList } from '../../App';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Department = { id: number; name: string };
type Asset = {
  id: number;
  number: string;
  name: string;
  serial: string;
  model: string;
  location: string;
};

export function NewRequestScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'NewRequest'>) {
  const [name, setName] = useState('');
  const [symptom, setSymptom] = useState('');
  const [phone, setPhone] = useState('');
  const [qty, setQty] = useState('1');
  const [departmentId, setDepartmentId] = useState<number | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [requester, setRequester] = useState('');
  const [assetQuery, setAssetQuery] = useState('');
  const [assetHits, setAssetHits] = useState<Asset[]>([]);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const nameEdited = useRef(false);
  const scanLock = useRef(false);
  const [permission, requestPermission] = useCameraPermissions();

  useEffect(() => {
    api<{ departments: Department[]; phone: string; requester: string }>('/form-options')
      .then((data) => {
        setDepartments(data.departments || []);
        setPhone(data.phone || '');
        setRequester(data.requester || '');
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    const text = assetQuery.trim();
    if (text.length < 2) {
      setAssetHits([]);
      return;
    }
    const timer = setTimeout(() => {
      api<{ assets: Asset[] }>(`/assets?q=${encodeURIComponent(text)}`)
        .then((data) => setAssetHits(data.assets || []))
        .catch((err: Error) => setError(err.message));
    }, 300);
    return () => clearTimeout(timer);
  }, [assetQuery]);

  function applyAsset(next: Asset) {
    setAsset(next);
    setAssetQuery('');
    setAssetHits([]);
    setError('');
    if (!nameEdited.current) {
      setName(next.name || '');
    }
  }

  async function lookupAsset(code: string) {
    const data = await api<{ asset: Asset }>(`/assets/lookup?code=${encodeURIComponent(code)}`);
    applyAsset(data.asset);
  }

  async function openScanner() {
    if (!permission?.granted) {
      const result = await requestPermission();
      if (!result.granted) {
        setError('ต้องอนุญาตใช้กล้องเพื่อสแกน QR ทรัพย์สิน');
        return;
      }
    }
    scanLock.current = false;
    setScanning(true);
  }

  async function onBarcode(code: string) {
    if (scanLock.current) {
      return;
    }
    scanLock.current = true;
    try {
      await lookupAsset(code);
      setScanning(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ไม่พบทรัพย์สิน');
      setTimeout(() => {
        scanLock.current = false;
      }, 1200);
    }
  }

  async function submit() {
    if (!name.trim()) {
      setError('กรุณาระบุเรื่องที่แจ้งซ่อม');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const data = await api<{ request: { id: number } }>('/requests', {
        method: 'POST',
        body: {
          name: name.trim(),
          symptom: symptom.trim(),
          phone: phone.trim(),
          qty: Number(qty) || 1,
          department_id: departmentId,
          asset_id: asset?.id || null,
        },
      });
      navigation.replace('JobDetail', { id: data.request.id });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'บันทึกไม่สำเร็จ');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ScrollView style={styles.root} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {requester ? <Text style={styles.kicker}>ผู้แจ้ง {requester}</Text> : null}
        <Text style={styles.label}>ทรัพย์สิน</Text>
        <View style={styles.assetRow}>
          <TextInput
            style={[styles.input, styles.assetInput]}
            value={assetQuery}
            onChangeText={setAssetQuery}
            placeholder="ค้นหาเลขที่ หรือชื่อ"
            placeholderTextColor={colors.muted}
          />
          <Pressable style={styles.scan} onPress={openScanner}>
            <Text style={styles.scanText}>QR</Text>
          </Pressable>
        </View>
        {assetHits.map((hit) => (
          <Pressable key={hit.id} style={styles.hit} onPress={() => applyAsset(hit)}>
            <Text style={styles.hitTitle}>{hit.number || hit.name}</Text>
            <Text style={styles.hitMeta}>{hit.number ? hit.name : hit.serial}</Text>
          </Pressable>
        ))}
        {asset ? (
          <View style={styles.assetCard}>
            <View style={styles.assetHead}>
              <Text style={styles.assetNumber}>{asset.number || asset.name}</Text>
              <Pressable onPress={() => setAsset(null)}>
                <Text style={styles.link}>เอาออก</Text>
              </Pressable>
            </View>
            {asset.number ? <Text style={styles.assetName}>{asset.name}</Text> : null}
            {asset.serial ? <Text style={styles.assetMeta}>ซีเรียล {asset.serial}</Text> : null}
            {asset.model ? <Text style={styles.assetMeta}>รุ่น {asset.model}</Text> : null}
            {asset.location ? <Text style={styles.assetMeta}>สถานที่ {asset.location}</Text> : null}
          </View>
        ) : null}
        <Text style={styles.label}>เรื่อง</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={(value) => {
            nameEdited.current = true;
            setName(value);
          }}
          placeholder="เช่น แอร์ไม่เย็น"
          placeholderTextColor={colors.muted}
        />
        <Text style={styles.label}>อาการชำรุด</Text>
        <TextInput
          style={[styles.input, styles.area]}
          value={symptom}
          onChangeText={setSymptom}
          placeholder="รายละเอียดที่ช่างควรทราบ"
          placeholderTextColor={colors.muted}
          multiline
        />
        <Text style={styles.label}>ฝ่าย / งาน / ตึก</Text>
        <View style={styles.chips}>
          {departments.map((department) => {
            const on = departmentId === department.id;
            return (
              <Pressable
                key={department.id}
                style={[styles.chip, on && styles.chipOn]}
                onPress={() => setDepartmentId(on ? null : department.id)}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>{department.name}</Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.row}>
          <View style={styles.half}>
            <Text style={styles.label}>โทร</Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              placeholder="เบอร์ติดต่อ"
              placeholderTextColor={colors.muted}
            />
          </View>
          <View style={styles.half}>
            <Text style={styles.label}>จำนวน</Text>
            <TextInput
              style={styles.input}
              value={qty}
              onChangeText={setQty}
              keyboardType="number-pad"
            />
          </View>
        </View>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable style={[styles.button, busy && styles.buttonOff]} onPress={submit} disabled={busy}>
          <Text style={styles.buttonText}>{busy ? 'กำลังส่ง...' : 'ส่งแจ้งซ่อม'}</Text>
        </Pressable>
      </ScrollView>
      <Modal visible={scanning} animationType="slide" onRequestClose={() => setScanning(false)}>
        <View style={styles.cameraWrap}>
          <CameraView
            style={styles.camera}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
            onBarcodeScanned={({ data }) => onBarcode(data)}
          />
          <View style={styles.cameraBar}>
            <Text style={styles.cameraHint}>สแกน QR ทรัพย์สิน</Text>
            <Pressable onPress={() => setScanning(false)}>
              <Text style={styles.cameraClose}>ปิด</Text>
            </Pressable>
          </View>
          {error ? <Text style={styles.cameraError}>{error}</Text> : null}
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, paddingBottom: 40 },
  kicker: { color: colors.muted, fontFamily: fonts.regular, marginBottom: 8 },
  label: { marginTop: 12, marginBottom: 6, fontFamily: fonts.medium, color: colors.ink },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontFamily: fonts.regular,
    color: colors.ink,
    fontSize: 16,
  },
  assetRow: { flexDirection: 'row', gap: 8 },
  assetInput: { flex: 1 },
  scan: {
    width: 56,
    borderRadius: 12,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scanText: { color: '#fff', fontFamily: fonts.bold, fontSize: 16 },
  hit: {
    marginTop: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 10,
  },
  hitTitle: { fontFamily: fonts.semiBold, color: colors.ink },
  hitMeta: { marginTop: 2, color: colors.muted, fontFamily: fonts.regular },
  assetCard: {
    marginTop: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.brand,
    borderRadius: 14,
    padding: 12,
  },
  assetHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  assetNumber: { flex: 1, fontFamily: fonts.semiBold, color: colors.ink, marginRight: 8 },
  assetName: { marginTop: 4, fontFamily: fonts.regular, color: colors.ink },
  assetMeta: { marginTop: 2, color: colors.muted, fontFamily: fonts.regular },
  link: { color: colors.brand, fontFamily: fonts.semiBold },
  area: { minHeight: 110, textAlignVertical: 'top' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line },
  chipOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  chipText: { fontFamily: fonts.medium, color: colors.ink },
  chipTextOn: { color: '#fff' },
  row: { flexDirection: 'row', gap: 10 },
  half: { flex: 1 },
  error: { color: colors.danger, marginTop: 12, fontFamily: fonts.regular },
  button: { marginTop: 20, backgroundColor: colors.brand, borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  buttonOff: { opacity: 0.6 },
  buttonText: { color: '#fff', fontFamily: fonts.semiBold, fontSize: 16 },
  cameraWrap: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  cameraBar: {
    position: 'absolute',
    top: 54,
    left: 16,
    right: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cameraHint: { color: '#fff', fontFamily: fonts.semiBold, fontSize: 18 },
  cameraClose: { color: '#fff', fontFamily: fonts.semiBold, fontSize: 16 },
  cameraError: {
    position: 'absolute',
    bottom: 48,
    left: 16,
    right: 16,
    color: '#fff',
    textAlign: 'center',
    fontFamily: fonts.regular,
  },
});
