import React, { useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator, ScrollView, Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

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

  // Google Sign-In requires native module — guide for real device setup
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

        {/* Icon + title */}
        <View style={styles.hero}>
          <Text style={styles.icon}>⚖️</Text>
          <Text style={styles.title}>Ethical AI</Text>
          <Text style={styles.subtitle}>AI-powered ethical reasoning & risk detection</Text>
        </View>

        {/* Card */}
        <BlurView intensity={20} tint="dark" style={styles.card}>
          <View style={styles.cardInner}>
            <Text style={styles.cardLabel}>SIGN IN TO CONTINUE</Text>

            {/* Google button */}
            <TouchableOpacity
              style={styles.googleBtn}
              onPress={signInWithGoogle}
              activeOpacity={0.8}
            >
              <LinearGradient
                colors={["#7c3aed", "#4f46e5"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.btnGradient}
              >
                {loading === "google" ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnText}>Continue with Google</Text>
                )}
              </LinearGradient>
            </TouchableOpacity>

            {/* Divider */}
            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>OR</Text>
              <View style={styles.dividerLine} />
            </View>

            {/* Guest button */}
            <TouchableOpacity
              style={styles.guestBtn}
              onPress={continueAsGuest}
              activeOpacity={0.7}
              disabled={loading === "guest"}
            >
              {loading === "guest" ? (
                <ActivityIndicator color="rgba(255,255,255,0.5)" />
              ) : (
                <Text style={styles.guestBtnText}>Continue as Guest</Text>
              )}
            </TouchableOpacity>

            <Text style={styles.privacyNote}>
              Your personal data is never stored.{"\n"}Only anonymised usage metadata is logged.
            </Text>
          </View>
        </BlurView>
      </ScrollView>
    </LinearGradient>
  );
}

const ACCENT = "#a78bfa";

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: {
    flexGrow: 1, justifyContent: "center",
    paddingHorizontal: 24, paddingVertical: 60,
  },
  hero: { alignItems: "center", marginBottom: 40 },
  icon: { fontSize: 56, marginBottom: 12 },
  title: {
    fontSize: 34, fontWeight: "700", color: "#e0d7ff",
    letterSpacing: -0.5, marginBottom: 8,
  },
  subtitle: {
    fontSize: 14, color: "rgba(255,255,255,0.5)",
    textAlign: "center", lineHeight: 20,
  },
  card: {
    borderRadius: 24, overflow: "hidden",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.2)",
  },
  cardInner: {
    padding: 28, backgroundColor: "rgba(255,255,255,0.07)",
  },
  cardLabel: {
    fontSize: 11, fontWeight: "600", color: "rgba(255,255,255,0.4)",
    letterSpacing: 1.2, textAlign: "center", marginBottom: 20,
  },
  googleBtn: { borderRadius: 14, overflow: "hidden", marginBottom: 16 },
  btnGradient: {
    paddingVertical: 16, alignItems: "center", justifyContent: "center",
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  divider: {
    flexDirection: "row", alignItems: "center", marginVertical: 16,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "rgba(255,255,255,0.1)" },
  dividerText: {
    fontSize: 11, color: "rgba(255,255,255,0.3)",
    marginHorizontal: 12, fontWeight: "500",
  },
  guestBtn: {
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
    borderRadius: 14, paddingVertical: 14,
    alignItems: "center", backgroundColor: "rgba(255,255,255,0.05)",
  },
  guestBtnText: { color: "rgba(255,255,255,0.55)", fontSize: 15, fontWeight: "500" },
  privacyNote: {
    fontSize: 11, color: "rgba(255,255,255,0.28)",
    textAlign: "center", lineHeight: 18, marginTop: 20,
  },
});
