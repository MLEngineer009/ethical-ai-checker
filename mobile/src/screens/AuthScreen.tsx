import React, { useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator, ScrollView, Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const ACCENT = "#a78bfa";

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <View style={styles.statItem}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function CaseItem({ verdict, verdictStyle, text }: { verdict: string; verdictStyle: object; text: string }) {
  return (
    <View style={styles.caseItem}>
      <View style={[styles.caseVerdict, verdictStyle]}>
        <Text style={styles.caseVerdictText}>{verdict}</Text>
      </View>
      <Text style={styles.caseText}>{text}</Text>
    </View>
  );
}

function RegItem({ dot, name, detail, fine }: { dot: string; name: string; detail: string; fine: string }) {
  return (
    <View style={styles.regItem}>
      <View style={[styles.regDot, dot === "live" ? styles.regDotLive : styles.regDotSoon]} />
      <View style={styles.regBody}>
        <Text style={styles.regName}>{name}</Text>
        <Text style={styles.regDetail}>{detail}</Text>
      </View>
      <View style={styles.regFineWrap}>
        <Text style={styles.regFine}>{fine}</Text>
      </View>
    </View>
  );
}

// ── Main screen ────────────────────────────────────────────────────────────────

export function AuthScreen() {
  const { signIn } = useAuth();
  const [loading, setLoading] = useState<"google" | "guest" | null>(null);

  const continueAsGuest = async () => {
    setLoading("guest");
    try {
      const auth = await api.guestAuth();
      signIn({ token: auth.token, name: "Guest", picture: "", isGuest: true });
    } catch (e: any) {
      Alert.alert("Error", e.message || "Could not start guest session.");
    } finally {
      setLoading(null);
    }
  };

  const signInWithGoogle = () => {
    Alert.alert(
      "Google Sign-In",
      "Google SSO requires native setup.\n\nFor now, use Continue as Guest or see SETUP.md to configure the GoogleSignIn native module.",
      [{ text: "OK" }]
    );
  };

  return (
    <LinearGradient
      colors={["#0f0c29", "#302b63", "#24243e"]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.icon}>🛡️</Text>
          <Text style={styles.title}>Pragma</Text>
          <Text style={styles.subtitle}>
            Block risky AI decisions{"\n"}before they become lawsuits.
          </Text>
        </View>

        {/* Value bullets */}
        <View style={styles.bullets}>
          {[
            { icon: "🛡", label: "AI Decision Firewall", desc: "Auto-block or flag high-risk decisions before they execute" },
            { icon: "⚖", label: "Regulatory mapping", desc: "Every flag linked to EEOC, GDPR, EU AI Act, ADA, and more" },
            { icon: "↓", label: "Audit-ready PDF reports", desc: "One-tap documentation your compliance team can hand to regulators" },
            { icon: "⚡", label: "API-first, drop-in", desc: "One call before your decision commits, works with any stack" },
          ].map(b => (
            <View key={b.label} style={styles.bullet}>
              <View style={styles.bulletDot}><Text style={styles.bulletIcon}>{b.icon}</Text></View>
              <Text style={styles.bulletText}>
                <Text style={styles.bulletBold}>{b.label}</Text>
                {"  "}{b.desc}
              </Text>
            </View>
          ))}
        </View>

        {/* Stats bar */}
        <Text style={styles.sectionLabel}>THE RISK IS REAL</Text>
        <View style={styles.statsGrid}>
          <StatItem value="$365K" label={"First EEOC AI hiring\nsettlement — 2023"} />
          <StatItem value="€35M"  label={"EU AI Act max fine\nfor high-risk violations"} />
          <StatItem value="99%"   label={"Fortune 500 use AI\nhiring automation"} />
          <StatItem value="$1,500" label={"NYC per-day penalty\nfor non-compliance"} />
        </View>

        {/* Real cases */}
        <Text style={styles.sectionLabel}>REAL CASES · REAL CONSEQUENCES</Text>
        <CaseItem
          verdict="SETTLED $365K"
          verdictStyle={styles.verdictRed}
          text="EEOC v. iTutorGroup (2023) — AI auto-rejected applicants 55+. First EEOC settlement involving AI discrimination."
        />
        <CaseItem
          verdict="CLASS ACTION"
          verdictStyle={styles.verdictYellow}
          text="Mobley v. Workday (2025) — AI screening alleged to discriminate by race, age & disability. Class certified. Millions of applicants."
        />
        <CaseItem
          verdict="TOOL SCRAPPED"
          verdictStyle={styles.verdictPurple}
          text="Amazon AI Hiring (2018) — Penalized résumés with 'women's' and excluded all-women's college graduates. Project abandoned."
        />

        {/* Regulatory deadlines */}
        <Text style={styles.sectionLabel}>REGULATORY DEADLINES</Text>
        <RegItem dot="live" name="NYC Local Law 144"    detail="Mandatory bias audits for AI hiring · In force July 2023"         fine="$1,500/day" />
        <RegItem dot="live" name="GDPR Article 22"      detail="Right to human review of automated decisions · EU residents"        fine="4% revenue" />
        <RegItem dot="soon" name="EU AI Act — Aug 2026" detail="Hiring, credit & healthcare AI must document & test for bias"       fine="€35M or 7%" />

        {/* Auth card */}
        <BlurView intensity={20} tint="dark" style={styles.card}>
          <View style={styles.cardInner}>
            <Text style={styles.cardLabel}>TRY THE FIREWALL FREE</Text>
            <Text style={styles.cardSub}>No account required — analyze your first decision in seconds</Text>

            <TouchableOpacity style={styles.googleBtn} onPress={signInWithGoogle} activeOpacity={0.8}>
              <LinearGradient
                colors={["#7c3aed", "#4f46e5"]}
                start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                style={styles.btnGradient}
              >
                {loading === "google"
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.btnText}>Continue with Google</Text>}
              </LinearGradient>
            </TouchableOpacity>

            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>OR</Text>
              <View style={styles.dividerLine} />
            </View>

            <TouchableOpacity
              style={styles.guestBtn}
              onPress={continueAsGuest}
              activeOpacity={0.7}
              disabled={loading === "guest"}
            >
              {loading === "guest"
                ? <ActivityIndicator color="rgba(255,255,255,0.5)" />
                : <Text style={styles.guestBtnText}>Continue as Guest</Text>}
            </TouchableOpacity>

            <Text style={styles.privacyNote}>
              No decision text stored. Anonymous metadata only.
            </Text>
          </View>
        </BlurView>

        <View style={{ height: 40 }} />
      </ScrollView>
    </LinearGradient>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingTop: 60, paddingBottom: 40 },

  // Hero
  hero: { alignItems: "center", marginBottom: 32 },
  icon: { fontSize: 52, marginBottom: 10 },
  title: { fontSize: 32, fontWeight: "700", color: "#e0d7ff", letterSpacing: -0.5, marginBottom: 10 },
  subtitle: { fontSize: 18, fontWeight: "700", color: "#fff", textAlign: "center", lineHeight: 26 },

  // Bullets
  bullets: { marginBottom: 28 },
  bullet: { flexDirection: "row", alignItems: "flex-start", gap: 10, marginBottom: 10 },
  bulletDot: {
    width: 22, height: 22, borderRadius: 11,
    backgroundColor: "rgba(167,139,250,0.15)",
    alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1,
  },
  bulletIcon: { fontSize: 11 },
  bulletText: { flex: 1, fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 19 },
  bulletBold: { color: "#fff", fontWeight: "700" },

  // Section label
  sectionLabel: {
    fontSize: 10, fontWeight: "700", letterSpacing: 1.2,
    color: "rgba(255,255,255,0.3)", marginBottom: 10,
  },

  // Stats
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 24 },
  statItem: {
    width: "47%",
    backgroundColor: "rgba(0,0,0,0.25)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
    borderRadius: 12, padding: 14,
  },
  statValue: { fontSize: 22, fontWeight: "800", color: "#e0d7ff", marginBottom: 4 },
  statLabel: { fontSize: 11, color: "rgba(255,255,255,0.45)", lineHeight: 15 },

  // Cases
  caseItem: {
    flexDirection: "row", alignItems: "flex-start", gap: 10,
    backgroundColor: "rgba(0,0,0,0.2)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.07)",
    borderRadius: 10, padding: 12, marginBottom: 7,
  },
  caseVerdict: { borderRadius: 20, paddingHorizontal: 8, paddingVertical: 3, flexShrink: 0, marginTop: 1 },
  caseVerdictText: { fontSize: 9, fontWeight: "700", letterSpacing: 0.3 },
  verdictRed:    { backgroundColor: "rgba(248,113,113,0.15)", borderWidth: 1, borderColor: "rgba(248,113,113,0.3)" },
  verdictYellow: { backgroundColor: "rgba(251,191,36,0.15)",  borderWidth: 1, borderColor: "rgba(251,191,36,0.3)"  },
  verdictPurple: { backgroundColor: "rgba(167,139,250,0.15)", borderWidth: 1, borderColor: "rgba(167,139,250,0.3)" },
  caseText: { flex: 1, fontSize: 12, color: "rgba(255,255,255,0.55)", lineHeight: 17 },

  // Regulatory
  regItem: {
    flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: "rgba(0,0,0,0.2)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.07)",
    borderRadius: 10, padding: 12, marginBottom: 7,
  },
  regDot: { width: 8, height: 8, borderRadius: 4, flexShrink: 0 },
  regDotLive: { backgroundColor: "#f87171" },
  regDotSoon: { backgroundColor: "#fbbf24" },
  regBody: { flex: 1 },
  regName:   { fontSize: 12, fontWeight: "700", color: "#fff", marginBottom: 2 },
  regDetail: { fontSize: 11, color: "rgba(255,255,255,0.45)", lineHeight: 15 },
  regFineWrap: {
    backgroundColor: "rgba(248,113,113,0.12)",
    borderWidth: 1, borderColor: "rgba(248,113,113,0.2)",
    borderRadius: 20, paddingHorizontal: 8, paddingVertical: 3,
  },
  regFine: { fontSize: 10, fontWeight: "700", color: "#fca5a5" },

  // Auth card
  card: { borderRadius: 24, overflow: "hidden", borderWidth: 1, borderColor: "rgba(255,255,255,0.2)", marginTop: 8 },
  cardInner: { padding: 28, backgroundColor: "rgba(255,255,255,0.07)" },
  cardLabel: {
    fontSize: 11, fontWeight: "700", color: ACCENT,
    letterSpacing: 1.2, textAlign: "center", marginBottom: 6,
  },
  cardSub: {
    fontSize: 13, color: "rgba(255,255,255,0.45)",
    textAlign: "center", lineHeight: 18, marginBottom: 22,
  },
  googleBtn: { borderRadius: 14, overflow: "hidden", marginBottom: 16 },
  btnGradient: { paddingVertical: 16, alignItems: "center", justifyContent: "center" },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  divider: { flexDirection: "row", alignItems: "center", marginVertical: 16 },
  dividerLine: { flex: 1, height: 1, backgroundColor: "rgba(255,255,255,0.1)" },
  dividerText: { fontSize: 11, color: "rgba(255,255,255,0.3)", marginHorizontal: 12, fontWeight: "500" },
  guestBtn: {
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
    borderRadius: 14, paddingVertical: 14,
    alignItems: "center", backgroundColor: "rgba(255,255,255,0.05)",
  },
  guestBtnText: { color: "rgba(255,255,255,0.55)", fontSize: 15, fontWeight: "500" },
  privacyNote: {
    fontSize: 11, color: "rgba(255,255,255,0.25)",
    textAlign: "center", lineHeight: 17, marginTop: 18,
  },
});
