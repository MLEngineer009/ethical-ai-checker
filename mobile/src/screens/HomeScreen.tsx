import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { GlassCard } from "../components/GlassCard";
import { useAuth } from "../context/AuthContext";
import { api, Question } from "../services/api";
import { RootStackParamList } from "../../App";

type Props = { navigation: NativeStackNavigationProp<RootStackParamList, "Main"> };

const CATEGORIES = [
  { key: "hiring",     label: "Hiring",     icon: "🧑‍💼" },
  { key: "workplace",  label: "Workplace",  icon: "🏢" },
  { key: "finance",    label: "Finance",    icon: "💰" },
  { key: "healthcare", label: "Healthcare", icon: "🏥" },
  { key: "policy",     label: "Policy",     icon: "📋" },
  { key: "personal",   label: "Personal",   icon: "👤" },
  { key: "other",      label: "Other",      icon: "💡" },
];

const ACCENT = "#a78bfa";

// ── Individual question renderers ────────────────────────────────────────────

function TextQuestion({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  return (
    <TextInput
      value={value}
      onChangeText={onChange}
      placeholder={q.placeholder || ""}
      placeholderTextColor="rgba(255,255,255,0.3)"
      style={styles.textInput}
    />
  );
}

function SelectQuestion({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.toggleRow}>
      {(q.options || []).map(opt => (
        <TouchableOpacity
          key={opt}
          onPress={() => onChange(value === opt ? "" : opt)}
          style={[styles.toggleBtn, value === opt && styles.toggleBtnActive]}
          activeOpacity={0.75}
        >
          <Text style={[styles.toggleBtnText, value === opt && styles.toggleBtnTextActive]}>{opt}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

function ToggleQuestion({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  return (
    <View style={styles.toggleRow}>
      {(q.options || []).map(opt => (
        <TouchableOpacity
          key={opt}
          onPress={() => onChange(value === opt ? "" : opt)}
          style={[styles.toggleBtn, value === opt && styles.toggleBtnActive]}
          activeOpacity={0.75}
        >
          <Text style={[styles.toggleBtnText, value === opt && styles.toggleBtnTextActive]}>{opt}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function MultiSelectQuestion({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  const selected = value ? value.split(",").map(s => s.trim()).filter(Boolean) : [];
  const toggle = (opt: string) => {
    const next = selected.includes(opt)
      ? selected.filter(s => s !== opt)
      : [...selected, opt];
    onChange(next.join(", "));
  };
  return (
    <View style={styles.chipsWrap}>
      {(q.options || []).map(opt => {
        const active = selected.includes(opt);
        return (
          <TouchableOpacity
            key={opt}
            onPress={() => toggle(opt)}
            style={[styles.chip, active && styles.chipActive]}
            activeOpacity={0.75}
          >
            <Text style={[styles.chipText, active && styles.chipTextActive]}>{opt}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function QuestionBlock({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  return (
    <View style={styles.questionBlock}>
      <View style={styles.questionLabelRow}>
        <Text style={styles.questionLabel}>{q.label}</Text>
        {q.required && <Text style={styles.requiredBadge}>required</Text>}
      </View>
      {q.type === "text" && <TextQuestion q={q} value={value} onChange={onChange} />}
      {q.type === "select" && <SelectQuestion q={q} value={value} onChange={onChange} />}
      {q.type === "toggle" && <ToggleQuestion q={q} value={value} onChange={onChange} />}
      {q.type === "multiselect" && <MultiSelectQuestion q={q} value={value} onChange={onChange} />}
    </View>
  );
}

// ── Fallback generic fields for "other" ──────────────────────────────────────

interface ContextField { id: string; key: string; value: string; }

function GenericFields({ fields, setFields }: {
  fields: ContextField[];
  setFields: React.Dispatch<React.SetStateAction<ContextField[]>>;
}) {
  const addField = () => setFields(f => [...f, { id: Date.now().toString(), key: "", value: "" }]);
  const removeField = (id: string) => setFields(f => f.filter(x => x.id !== id));
  const updateField = (id: string, prop: "key" | "value", val: string) =>
    setFields(f => f.map(x => x.id === id ? { ...x, [prop]: val } : x));

  return (
    <>
      <View style={styles.contextHeader}>
        <Text style={styles.label}>CONTEXT</Text>
        <TouchableOpacity onPress={addField} style={styles.addBtn}>
          <Text style={styles.addBtnText}>+ Add Field</Text>
        </TouchableOpacity>
      </View>
      {fields.map(f => (
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
    </>
  );
}

// ── Main screen ──────────────────────────────────────────────────────────────

export function HomeScreen({ navigation }: Props) {
  const { user, signOut } = useAuth();
  const [decision, setDecision] = useState("");
  const [category, setCategory] = useState("hiring");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  // fallback fields for "other"
  const [fields, setFields] = useState<ContextField[]>([
    { id: "1", key: "", value: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadQuestions = useCallback(async (cat: string) => {
    if (cat === "other") { setQuestions([]); return; }
    setLoadingQuestions(true);
    try {
      const res = await api.getQuestions(cat);
      setQuestions(res.questions);
      setAnswers({});
    } catch {
      setQuestions([]);
    } finally {
      setLoadingQuestions(false);
    }
  }, []);

  useEffect(() => {
    setDecision("");
    setError("");
    loadQuestions(category);
  }, [category]);

  const setAnswer = (key: string, value: string) =>
    setAnswers(prev => ({ ...prev, [key]: value }));

  const buildContext = (): Record<string, string> => {
    if (category === "other") {
      const ctx: Record<string, string> = {};
      for (const f of fields) {
        const k = f.key.trim(); const v = f.value.trim();
        if (k && v) ctx[k] = v;
      }
      return ctx;
    }
    const ctx: Record<string, string> = {};
    for (const q of questions) {
      const v = (answers[q.key] || "").trim();
      if (v) ctx[q.key] = v;
    }
    return ctx;
  };

  const validate = (): string | null => {
    if (!decision.trim()) return "Please enter a decision.";
    if (category === "other") {
      const ctx = buildContext();
      if (!Object.keys(ctx).length) return "Please fill in at least one context field.";
    } else {
      for (const q of questions) {
        if (q.required && !(answers[q.key] || "").trim()) {
          return `Please answer: "${q.label}"`;
        }
      }
    }
    return null;
  };

  const evaluate = async () => {
    const err = validate();
    if (err) { setError(err); return; }
    if (!user) return;

    setError(""); setLoading(true);
    try {
      const ctx = buildContext();
      const result = await api.evaluate(decision.trim(), ctx, user.token, category);
      navigation.navigate("Results", { analysis: result, decision: decision.trim(), context: ctx });
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

          {/* Context — guided questions or generic fields */}
          <GlassCard>
            <Text style={styles.label}>CONTEXT</Text>
            {category === "other" ? (
              <GenericFields fields={fields} setFields={setFields} />
            ) : loadingQuestions ? (
              <ActivityIndicator color={ACCENT} style={{ marginVertical: 16 }} />
            ) : (
              questions.map(q => (
                <QuestionBlock
                  key={q.key}
                  q={q}
                  value={answers[q.key] || ""}
                  onChange={v => setAnswer(q.key, v)}
                />
              ))
            )}
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
  label: { fontSize: 11, fontWeight: "700", color: ACCENT, letterSpacing: 1.1, marginBottom: 10 },
  pillRow: { flexDirection: "row", gap: 8, paddingBottom: 2 },
  pill: {
    flexDirection: "row", alignItems: "center", gap: 5,
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  pillActive: { backgroundColor: "rgba(167,139,250,0.18)", borderColor: "rgba(167,139,250,0.6)" },
  pillIcon: { fontSize: 14 },
  pillText: { fontSize: 13, fontWeight: "500", color: "rgba(255,255,255,0.55)" },
  pillTextActive: { color: ACCENT, fontWeight: "700" },
  textarea: {
    color: "#fff", fontSize: 15, minHeight: 90,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    padding: 12, lineHeight: 22,
  },
  // Guided questions
  questionBlock: { marginBottom: 18 },
  questionLabelRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  questionLabel: { fontSize: 13, fontWeight: "600", color: "#e0d7ff", flex: 1 },
  requiredBadge: {
    fontSize: 9, fontWeight: "700", color: ACCENT, letterSpacing: 0.5,
    textTransform: "uppercase", opacity: 0.7,
  },
  textInput: {
    color: "#fff", fontSize: 14,
    backgroundColor: "rgba(255,255,255,0.07)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 12, paddingVertical: 10,
  },
  toggleRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  toggleBtn: {
    paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  toggleBtnActive: { backgroundColor: "rgba(167,139,250,0.18)", borderColor: ACCENT },
  toggleBtnText: { fontSize: 13, fontWeight: "600", color: "rgba(255,255,255,0.55)" },
  toggleBtnTextActive: { color: ACCENT },
  chipsWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  chipActive: { backgroundColor: "rgba(167,139,250,0.18)", borderColor: ACCENT },
  chipText: { fontSize: 12, fontWeight: "600", color: "rgba(255,255,255,0.55)" },
  chipTextActive: { color: ACCENT },
  // Generic fields
  contextHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  addBtn: {
    backgroundColor: "rgba(167,139,250,0.1)", borderRadius: 8,
    paddingHorizontal: 10, paddingVertical: 5,
    borderWidth: 1, borderColor: "rgba(167,139,250,0.3)", borderStyle: "dashed",
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
