import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { GlassCard } from "../components/GlassCard";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { RootStackParamList } from "../../App";

type Props = { navigation: NativeStackNavigationProp<RootStackParamList, "Home"> };

interface ContextField { id: string; key: string; value: string; }

const CATEGORIES = [
  { key: "hiring",     label: "Hiring",     icon: "🧑‍💼" },
  { key: "workplace",  label: "Workplace",  icon: "🏢" },
  { key: "finance",    label: "Finance",    icon: "💰" },
  { key: "healthcare", label: "Healthcare", icon: "🏥" },
  { key: "policy",     label: "Policy",     icon: "📋" },
  { key: "personal",   label: "Personal",   icon: "👤" },
  { key: "other",      label: "Other",      icon: "💡" },
];

export function HomeScreen({ navigation }: Props) {
  const { user, signOut } = useAuth();
  const [decision, setDecision] = useState("");
  const [category, setCategory] = useState("other");
  const [fields, setFields] = useState<ContextField[]>([
    { id: "1", key: "gender", value: "" },
    { id: "2", key: "experience", value: "" },
    { id: "3", key: "", value: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addField = () =>
    setFields(f => [...f, { id: Date.now().toString(), key: "", value: "" }]);

  const removeField = (id: string) =>
    setFields(f => f.filter(x => x.id !== id));

  const updateField = (id: string, prop: "key" | "value", val: string) =>
    setFields(f => f.map(x => x.id === id ? { ...x, [prop]: val } : x));

  const buildContext = () => {
    const ctx: Record<string, string> = {};
    for (const f of fields) {
      const k = f.key.trim(); const v = f.value.trim();
      if (k && v) ctx[k] = v;
    }
    return ctx;
  };

  const evaluate = async () => {
    const trimmed = decision.trim();
    const ctx = buildContext();
    if (!trimmed) { setError("Please enter a decision."); return; }
    if (!Object.keys(ctx).length) { setError("Please fill in at least one context field."); return; }
    if (!user) return;

    setError(""); setLoading(true);
    try {
      const result = await api.evaluate(trimmed, ctx, user.token, category);
      navigation.navigate("Results", { analysis: result, decision: trimmed, context: ctx });
    } catch (e: any) {
      if (e.status === 401) { signOut(); return; }
      setError(e.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient colors={["#0f0c29", "#302b63", "#24243e"]}
      start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.bg}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

          {/* User bar */}
          <View style={styles.userBar}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Text style={styles.userName}>{user?.name || "User"}</Text>
              {user?.isGuest && (
                <View style={styles.guestBadge}><Text style={styles.guestBadgeText}>GUEST</Text></View>
              )}
            </View>
            <TouchableOpacity onPress={signOut} style={styles.signOutBtn}>
              <Text style={styles.signOutText}>Sign Out</Text>
            </TouchableOpacity>
          </View>

          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.icon}>⚖️</Text>
            <Text style={styles.title}>Pragma</Text>
            <Text style={styles.subtitle}>Practical AI ethics for automated decisions</Text>
          </View>

          {/* Category selector */}
          <GlassCard>
            <Text style={styles.label}>DECISION CATEGORY</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.pillRow}>
              {CATEGORIES.map(cat => (
                <TouchableOpacity
                  key={cat.key}
                  onPress={() => setCategory(cat.key)}
                  style={[styles.pill, category === cat.key && styles.pillActive]}
                  activeOpacity={0.75}
                >
                  <Text style={styles.pillIcon}>{cat.icon}</Text>
                  <Text style={[styles.pillText, category === cat.key && styles.pillTextActive]}>
                    {cat.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </GlassCard>

          {/* Decision */}
          <GlassCard>
            <Text style={styles.label}>DECISION</Text>
            <TextInput
              value={decision}
              onChangeText={setDecision}
              placeholder="Describe the decision being evaluated…"
              placeholderTextColor="rgba(255,255,255,0.3)"
              multiline
              numberOfLines={4}
              style={styles.textarea}
              textAlignVertical="top"
            />
          </GlassCard>

          {/* Context */}
          <GlassCard>
            <View style={styles.contextHeader}>
              <Text style={styles.label}>CONTEXT</Text>
              <TouchableOpacity onPress={addField} style={styles.addBtn}>
                <Text style={styles.addBtnText}>+ Add Field</Text>
              </TouchableOpacity>
            </View>
            {fields.map((f) => (
              <View key={f.id} style={styles.fieldRow}>
                <TextInput
                  value={f.key}
                  onChangeText={v => updateField(f.id, "key", v)}
                  placeholder="Field name"
                  placeholderTextColor="rgba(167,139,250,0.4)"
                  style={[styles.fieldInput, styles.fieldKey]}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <TextInput
                  value={f.value}
                  onChangeText={v => updateField(f.id, "value", v)}
                  placeholder="Value"
                  placeholderTextColor="rgba(255,255,255,0.3)"
                  style={styles.fieldInput}
                />
                {fields.length > 1 && (
                  <TouchableOpacity onPress={() => removeField(f.id)} style={styles.removeBtn}>
                    <Text style={styles.removeBtnText}>✕</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </GlassCard>

          {/* Error */}
          {!!error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Evaluate button */}
          <TouchableOpacity onPress={evaluate} disabled={loading} activeOpacity={0.85}>
            <LinearGradient colors={["#7c3aed", "#4f46e5"]}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              style={[styles.evaluateBtn, loading && { opacity: 0.6 }]}>
              {loading
                ? <><ActivityIndicator color="#fff" /><Text style={styles.evaluateBtnText}> Analysing…</Text></>
                : <Text style={styles.evaluateBtnText}>Evaluate Decision</Text>
              }
            </LinearGradient>
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const ACCENT = "#a78bfa";

const styles = StyleSheet.create({
  bg: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingTop: 60, paddingBottom: 40 },
  userBar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    backgroundColor: "rgba(255,255,255,0.08)", borderRadius: 14,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
    paddingHorizontal: 16, paddingVertical: 10, marginBottom: 24,
  },
  userName: { fontSize: 13, fontWeight: "600", color: ACCENT },
  guestBadge: {
    backgroundColor: "rgba(251,191,36,0.12)", borderRadius: 20,
    paddingHorizontal: 8, paddingVertical: 2,
    borderWidth: 1, borderColor: "rgba(251,191,36,0.25)",
  },
  guestBadgeText: { fontSize: 9, fontWeight: "700", color: "#fbbf24", letterSpacing: 0.8 },
  signOutBtn: {
    backgroundColor: "rgba(248,113,113,0.12)", borderRadius: 8,
    paddingHorizontal: 12, paddingVertical: 6,
    borderWidth: 1, borderColor: "rgba(248,113,113,0.25)",
  },
  signOutText: { fontSize: 12, fontWeight: "600", color: "#fca5a5" },
  header: { alignItems: "center", marginBottom: 24 },
  icon: { fontSize: 42, marginBottom: 8 },
  title: { fontSize: 28, fontWeight: "700", color: "#e0d7ff", marginBottom: 4 },
  subtitle: { fontSize: 13, color: "rgba(255,255,255,0.5)", textAlign: "center" },
  label: {
    fontSize: 11, fontWeight: "700", color: ACCENT,
    letterSpacing: 1.1, marginBottom: 10,
  },
  // Category pills
  pillRow: { flexDirection: "row", gap: 8, paddingBottom: 2 },
  pill: {
    flexDirection: "row", alignItems: "center", gap: 5,
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  pillActive: {
    backgroundColor: "rgba(167,139,250,0.18)",
    borderColor: "rgba(167,139,250,0.6)",
  },
  pillIcon: { fontSize: 14 },
  pillText: { fontSize: 13, fontWeight: "500", color: "rgba(255,255,255,0.55)" },
  pillTextActive: { color: ACCENT, fontWeight: "700" },
  // Decision textarea
  textarea: {
    color: "#fff", fontSize: 15, minHeight: 90,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    padding: 12, lineHeight: 22,
  },
  contextHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  addBtn: {
    backgroundColor: "rgba(167,139,250,0.1)", borderRadius: 8,
    paddingHorizontal: 10, paddingVertical: 5,
    borderWidth: 1, borderColor: "rgba(167,139,250,0.3)",
    borderStyle: "dashed",
  },
  addBtnText: { fontSize: 12, fontWeight: "600", color: ACCENT },
  fieldRow: { flexDirection: "row", gap: 8, marginBottom: 8, alignItems: "center" },
  fieldInput: {
    flex: 1, color: "#fff", fontSize: 14,
    backgroundColor: "rgba(255,255,255,0.07)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 12, paddingVertical: 9,
  },
  fieldKey: { color: ACCENT, fontWeight: "600" },
  removeBtn: { padding: 4 },
  removeBtnText: { color: "rgba(255,255,255,0.3)", fontSize: 14 },
  errorBox: {
    backgroundColor: "rgba(248,113,113,0.15)", borderRadius: 12,
    borderWidth: 1, borderColor: "rgba(248,113,113,0.3)",
    padding: 12, marginBottom: 14,
  },
  errorText: { color: "#fca5a5", fontSize: 14, textAlign: "center" },
  evaluateBtn: {
    borderRadius: 14, paddingVertical: 16,
    flexDirection: "row", alignItems: "center", justifyContent: "center",
  },
  evaluateBtnText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
