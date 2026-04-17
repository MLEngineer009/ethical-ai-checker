import React, { useEffect, useRef, useState } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  Animated, Alert, ActivityIndicator, TextInput,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { File as FSFile, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { RouteProp } from "@react-navigation/native";
import { GlassCard } from "../components/GlassCard";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { RootStackParamList } from "../../App";

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, "Results">;
  route: RouteProp<RootStackParamList, "Results">;
};

const FRAMEWORKS = [
  { id: "kantian",     label: "Kantian Ethics",  color: "#a78bfa", key: "kantian_analysis" },
  { id: "utilitarian", label: "Utilitarianism",   color: "#818cf8", key: "utilitarian_analysis" },
  { id: "virtue",      label: "Virtue Ethics",    color: "#c084fc", key: "virtue_ethics_analysis" },
] as const;

export function ResultsScreen({ route }: Props) {
  const { analysis, decision, context } = route.params;
  const { user } = useAuth();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const confAnim = useRef(new Animated.Value(0)).current;

  // Counterfactual
  const [cfOpen, setCfOpen] = useState(false);
  const [cfKey, setCfKey] = useState("");
  const [cfValue, setCfValue] = useState("");
  const [cfLoading, setCfLoading] = useState(false);
  const [cfResult, setCfResult] = useState<null | {
    diff: { flags_added: string[]; flags_removed: string[]; confidence_delta: number };
    original: any; modified: any;
    changed_key: string; modified_value: string;
  }>(null);

  useEffect(() => {
    Animated.timing(confAnim, {
      toValue: analysis.confidence_score,
      duration: 1000,
      delay: 400,
      useNativeDriver: false,
    }).start();
  }, []);

  const toggle = (id: string) => setExpanded(e => e === id ? null : id);

  const runCounterfactual = async () => {
    if (!cfKey.trim() || !cfValue.trim() || !user) return;
    setCfLoading(true);
    setCfResult(null);
    try {
      const res = await api.counterfactual(
        decision, context, "other", cfKey.trim(), cfValue.trim(), user.token
      );
      setCfResult(res);
    } catch (e: any) {
      Alert.alert("Error", e.message || "Counterfactual failed.");
    } finally {
      setCfLoading(false);
    }
  };

  const downloadPDF = async () => {
    if (!user) return;
    setDownloading(true);
    try {
      const arrayBuffer = await api.generateReport(decision, context, analysis, user.token);
      const bytes = new Uint8Array(arrayBuffer);
      const file = new FSFile(Paths.document, "ethical-analysis-report.pdf");
      file.write(bytes);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, { mimeType: "application/pdf" });
      } else {
        Alert.alert("Saved", "PDF saved to your documents.");
      }
    } catch (e: any) {
      Alert.alert("Error", e.message || "Could not generate PDF.");
    } finally {
      setDownloading(false);
    }
  };

  const providerColor = (p: string) =>
    p === "claude" ? "#a78bfa" : p === "openai" ? "#34d399" : "rgba(255,255,255,0.4)";

  return (
    <LinearGradient colors={["#0f0c29", "#302b63", "#24243e"]}
      start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.bg}>
      <ScrollView contentContainerStyle={styles.scroll}>

        {/* Header */}
        <View style={styles.headerRow}>
          <Text style={styles.heading}>Analysis</Text>
          <View style={[styles.providerBadge, { borderColor: providerColor(analysis.provider) + "55" }]}>
            <Text style={[styles.providerText, { color: providerColor(analysis.provider) }]}>
              {analysis.provider.toUpperCase()}
            </Text>
          </View>
        </View>

        {/* Framework accordions */}
        {FRAMEWORKS.map(fw => {
          const isOpen = expanded === fw.id;
          const text = analysis[fw.key];
          return (
            <View key={fw.id} style={styles.accordionCard}>
              <TouchableOpacity onPress={() => toggle(fw.id)} style={styles.accordionHeader} activeOpacity={0.7}>
                <Text style={[styles.frameworkLabel, { color: fw.color }]}>{fw.label}</Text>
                <Text style={[styles.chevron, isOpen && styles.chevronOpen]}>▼</Text>
              </TouchableOpacity>
              {isOpen && (
                <View style={styles.accordionBody}>
                  <View style={[styles.divider, { backgroundColor: fw.color + "30" }]} />
                  <Text style={styles.analysisText}>{text}</Text>
                </View>
              )}
            </View>
          );
        })}

        {/* Risk flags */}
        <GlassCard>
          <Text style={styles.cardLabel}>⚠️ RISK DETECTION</Text>
          {analysis.risk_flags.length === 0 ? (
            <Text style={styles.noRisk}>✅ No significant risks detected</Text>
          ) : (
            <View style={styles.chipsWrap}>
              {analysis.risk_flags.map(flag => (
                <View key={flag} style={styles.chip}>
                  <Text style={styles.chipText}>{flag.replace(/_/g, " ").toUpperCase()}</Text>
                </View>
              ))}
            </View>
          )}
        </GlassCard>

        {/* Confidence */}
        <GlassCard>
          <Text style={styles.cardLabel}>CONFIDENCE SCORE</Text>
          <View style={styles.confRow}>
            <Text style={styles.confValue}>{Math.round(analysis.confidence_score * 100)}%</Text>
            <View style={styles.confBarBg}>
              <Animated.View style={[
                styles.confBarFill,
                { width: confAnim.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] }) }
              ]} />
            </View>
          </View>
        </GlassCard>

        {/* Recommendation */}
        <GlassCard>
          <Text style={styles.cardLabel}>💡 RECOMMENDATION</Text>
          <Text style={styles.recText}>{analysis.recommendation}</Text>
        </GlassCard>

        {/* Counterfactual */}
        <GlassCard>
          <TouchableOpacity onPress={() => { setCfOpen(o => !o); setCfResult(null); }} activeOpacity={0.8}>
            <Text style={styles.cardLabel}>🔁 COUNTERFACTUAL — WHAT IF A VALUE CHANGED?</Text>
          </TouchableOpacity>
          {cfOpen && (
            <View style={{ marginTop: 10 }}>
              <View style={styles.cfRow}>
                <TextInput
                  value={cfKey}
                  onChangeText={setCfKey}
                  placeholder="Context key  (e.g. gender)"
                  placeholderTextColor="rgba(255,255,255,0.3)"
                  style={[styles.cfInput, { flex: 1 }]}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <TextInput
                  value={cfValue}
                  onChangeText={setCfValue}
                  placeholder="New value"
                  placeholderTextColor="rgba(255,255,255,0.3)"
                  style={[styles.cfInput, { flex: 1 }]}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
              </View>
              <TouchableOpacity onPress={runCounterfactual} disabled={cfLoading} activeOpacity={0.85}>
                <LinearGradient colors={["#4f46e5", "#7c3aed"]}
                  start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                  style={[styles.cfRunBtn, cfLoading && { opacity: 0.6 }]}>
                  {cfLoading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.cfRunText}>Analyse</Text>}
                </LinearGradient>
              </TouchableOpacity>

              {cfResult && (
                <View style={styles.cfResultBox}>
                  <Text style={styles.cfResultTitle}>
                    "{cfResult.changed_key}" → "{cfResult.modified_value}"
                  </Text>
                  <Text style={styles.cfAdded}>
                    Risks added: {cfResult.diff.flags_added.length ? cfResult.diff.flags_added.join(", ") : "none"}
                  </Text>
                  <Text style={styles.cfRemoved}>
                    Risks removed: {cfResult.diff.flags_removed.length ? cfResult.diff.flags_removed.join(", ") : "none"}
                  </Text>
                  <Text style={[
                    styles.cfDelta,
                    { color: cfResult.diff.confidence_delta > 0 ? "#34d399" : cfResult.diff.confidence_delta < 0 ? "#fca5a5" : "rgba(255,255,255,0.5)" }
                  ]}>
                    Confidence delta: {cfResult.diff.confidence_delta > 0 ? "+" : ""}{Math.round(cfResult.diff.confidence_delta * 100)}%
                  </Text>
                </View>
              )}
            </View>
          )}
        </GlassCard>

        {/* Download PDF */}
        <TouchableOpacity onPress={downloadPDF} disabled={downloading} activeOpacity={0.85}>
          <LinearGradient colors={["#059669", "#10b981"]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            style={[styles.downloadBtn, downloading && { opacity: 0.6 }]}>
            {downloading
              ? <><ActivityIndicator color="#fff" /><Text style={styles.downloadText}> Generating PDF…</Text></>
              : <Text style={styles.downloadText}>⬇  Download PDF Report</Text>
            }
          </LinearGradient>
        </TouchableOpacity>

        <View style={{ height: 40 }} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 40 },
  headerRow: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", marginBottom: 16,
  },
  heading: { fontSize: 22, fontWeight: "700", color: "#fff" },
  providerBadge: {
    borderWidth: 1, borderRadius: 20,
    paddingHorizontal: 10, paddingVertical: 4,
    backgroundColor: "rgba(255,255,255,0.05)",
  },
  providerText: { fontSize: 10, fontWeight: "700", letterSpacing: 1 },

  // Accordion
  accordionCard: {
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 20, overflow: "hidden",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.18)",
    marginBottom: 12,
  },
  accordionHeader: {
    flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", padding: 18,
  },
  frameworkLabel: { fontSize: 11, fontWeight: "700", letterSpacing: 1 },
  chevron: { color: "rgba(255,255,255,0.4)", fontSize: 11 },
  chevronOpen: { transform: [{ rotate: "180deg" }] },
  accordionBody: { paddingHorizontal: 18, paddingBottom: 16 },
  divider: { height: 1, marginBottom: 12 },
  analysisText: { color: "rgba(255,255,255,0.82)", fontSize: 14, lineHeight: 22 },

  cardLabel: {
    fontSize: 11, fontWeight: "700", color: "#a78bfa",
    letterSpacing: 1.1, marginBottom: 10,
  },
  noRisk: { color: "#34d399", fontSize: 14 },
  chipsWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    backgroundColor: "rgba(248,113,113,0.14)", borderRadius: 20,
    paddingHorizontal: 10, paddingVertical: 5,
    borderWidth: 1, borderColor: "rgba(248,113,113,0.25)",
  },
  chipText: { color: "#fca5a5", fontSize: 10, fontWeight: "700", letterSpacing: 0.7 },

  confRow: { flexDirection: "row", alignItems: "center", gap: 14 },
  confValue: { fontSize: 32, fontWeight: "700", color: "#a78bfa", minWidth: 64 },
  confBarBg: {
    flex: 1, height: 8, backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 99, overflow: "hidden",
  },
  confBarFill: {
    height: "100%", backgroundColor: "#818cf8", borderRadius: 99,
  },
  recText: { color: "rgba(255,255,255,0.85)", fontSize: 14, lineHeight: 22 },

  downloadBtn: {
    borderRadius: 14, paddingVertical: 16,
    flexDirection: "row", alignItems: "center", justifyContent: "center",
  },
  downloadText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cfRow: { flexDirection: "row", gap: 8, marginBottom: 10 },
  cfInput: {
    color: "#fff", fontSize: 14,
    backgroundColor: "rgba(255,255,255,0.07)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 12, paddingVertical: 9,
  },
  cfRunBtn: { borderRadius: 12, paddingVertical: 12, alignItems: "center", justifyContent: "center" },
  cfRunText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  cfResultBox: {
    marginTop: 12, backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.1)", padding: 12,
  },
  cfResultTitle: { fontSize: 12, fontWeight: "700", color: "#e0d7ff", marginBottom: 8 },
  cfAdded:   { fontSize: 13, color: "#34d399", marginBottom: 4 },
  cfRemoved: { fontSize: 13, color: "#fca5a5", marginBottom: 4 },
  cfDelta:   { fontSize: 13 },
});
