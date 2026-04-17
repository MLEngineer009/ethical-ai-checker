import React, { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const ACCENT = "#a78bfa";

interface HistoryItem {
  timestamp: string;
  category: string;
  decision_words: number;
  provider: string;
  confidence: number;
  risk_count: number;
  risk_categories: string[];
}

export function HistoryScreen() {
  const { user } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    api.getStats(user.token)
      .then(data => setHistory(data.history || []))
      .catch(e => setError(e.message || "Failed to load history"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <LinearGradient colors={["#0f0c29", "#302b63", "#24243e"]}
      start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.bg}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.heading}>Decision History</Text>
        <Text style={styles.sub}>Metadata only — decision text is never stored.</Text>

        {loading && <ActivityIndicator color={ACCENT} style={{ marginTop: 40 }} />}
        {!!error && <Text style={styles.error}>{error}</Text>}

        {!loading && !error && history.length === 0 && (
          <Text style={styles.empty}>No evaluations yet. Run your first analysis!</Text>
        )}

        {history.map((h, i) => (
          <View key={i} style={styles.item}>
            <View style={styles.itemTop}>
              <Text style={styles.category}>{h.category.toUpperCase()}</Text>
              <Text style={styles.timestamp}>
                {new Date(h.timestamp).toLocaleDateString()}
              </Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.meta}>~{h.decision_words} words</Text>
              <Text style={styles.meta}>via {h.provider}</Text>
              <Text style={styles.meta}>{Math.round(h.confidence * 100)}% confidence</Text>
            </View>
            {h.risk_categories.length > 0 ? (
              <View style={styles.flagsRow}>
                {h.risk_categories.map(f => (
                  <View key={f} style={styles.flag}>
                    <Text style={styles.flagText}>{f}</Text>
                  </View>
                ))}
              </View>
            ) : (
              <Text style={styles.noRisk}>✅ No risks detected</Text>
            )}
          </View>
        ))}

        <View style={{ height: 40 }} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 40 },
  heading: { fontSize: 22, fontWeight: "700", color: "#e0d7ff", marginBottom: 6 },
  sub: { fontSize: 13, color: "rgba(255,255,255,0.4)", marginBottom: 20 },
  empty: { color: "rgba(255,255,255,0.4)", fontSize: 14, textAlign: "center", marginTop: 40 },
  error: { color: "#fca5a5", fontSize: 14, textAlign: "center", marginTop: 40 },
  item: {
    backgroundColor: "rgba(255,255,255,0.06)", borderRadius: 14,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
    padding: 14, marginBottom: 12,
  },
  itemTop: { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  category: { fontSize: 11, fontWeight: "700", color: ACCENT, letterSpacing: 0.8 },
  timestamp: { fontSize: 11, color: "rgba(255,255,255,0.4)" },
  metaRow: { flexDirection: "row", gap: 12, flexWrap: "wrap", marginBottom: 8 },
  meta: { fontSize: 12, color: "rgba(255,255,255,0.5)" },
  flagsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  flag: {
    backgroundColor: "rgba(248,113,113,0.12)", borderRadius: 20,
    paddingHorizontal: 10, paddingVertical: 3,
    borderWidth: 1, borderColor: "rgba(248,113,113,0.2)",
  },
  flagText: { fontSize: 10, fontWeight: "700", color: "#fca5a5" },
  noRisk: { fontSize: 12, color: "#34d399" },
});
