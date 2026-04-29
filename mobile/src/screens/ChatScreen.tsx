import React, { useState, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import { useAuth } from "../context/AuthContext";
import { BASE_URL } from "../services/api";

interface ChatMessage {
  role: "user" | "ai";
  content: string;
  firewallAction?: "block" | "override_required" | "allow";
  riskFlags?: string[];
  confidenceScore?: number;
  recommendation?: string;
}

const SCENARIOS = [
  { label: "🚫 Reject based on age", text: "Reject the 58-year-old applicant — she is overqualified." },
  { label: "🚫 Deny loan by location", text: "Deny this loan — the applicant lives in zip code 60620." },
  { label: "✅ Safe hiring question", text: "What interview questions should I use for a software engineering role?" },
  { label: "✅ Fair lending criteria", text: "What criteria should I use to evaluate loan applications fairly?" },
];

const CATEGORIES = [
  { key: "hiring", label: "🧑‍💼 Hiring" },
  { key: "finance", label: "💰 Finance" },
  { key: "healthcare", label: "🏥 Healthcare" },
  { key: "other", label: "💡 General" },
];

export function ChatScreen() {
  const { token } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [category, setCategory] = useState("hiring");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  async function sendMessage(text?: string) {
    const message = (text ?? inputText).trim();
    if (!message || busy) return;

    setInputText("");
    setBusy(true);
    setMessages(prev => [...prev, { role: "user", content: message }]);

    try {
      const res = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message, category }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: "ai",
        content: data.ai_response ?? "",
        firewallAction: data.firewall_action,
        riskFlags: data.risk_flags ?? [],
        confidenceScore: data.confidence_score,
        recommendation: data.recommendation,
      }]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: "ai", content: `Error: ${e.message}` }]);
    } finally {
      setBusy(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      {/* Category selector */}
      <View style={styles.categoryBar}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryScroll}>
          {CATEGORIES.map(c => (
            <TouchableOpacity key={c.key} style={[styles.catPill, category === c.key && styles.catPillActive]} onPress={() => setCategory(c.key)}>
              <Text style={[styles.catText, category === c.key && styles.catTextActive]}>{c.label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <ScrollView ref={scrollRef} style={styles.messages} contentContainerStyle={styles.messagesContent}>
        {messages.length === 0 && (
          <View style={styles.intro}>
            <Text style={styles.introIcon}>🛡️</Text>
            <Text style={styles.introTitle}>Compliance-aware AI assistant</Text>
            <Text style={styles.introSub}>Every message is evaluated by the Pragma firewall. Risky requests are blocked and the triggering regulations are shown.</Text>
            <Text style={styles.scenarioLabel}>TRY THESE EXAMPLES</Text>
            {SCENARIOS.map((s, i) => (
              <TouchableOpacity key={i} style={styles.scenarioBtn} onPress={() => sendMessage(s.text)}>
                <Text style={styles.scenarioBtnText}>{s.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {messages.map((msg, i) => (
          <View key={i}>
            {msg.role === "user" ? (
              <View style={styles.userRow}>
                <View style={styles.userBubble}>
                  <Text style={styles.userText}>{msg.content}</Text>
                </View>
              </View>
            ) : (
              <View style={styles.aiRow}>
                <Text style={styles.aiAvatar}>🛡️</Text>
                <View style={styles.aiBubbleWrap}>
                  {/* Firewall verdict badge */}
                  {msg.firewallAction && (() => {
                    const isBlock = msg.firewallAction === "block";
                    const isFlag = msg.firewallAction === "override_required";
                    const badgeStyle = isBlock ? styles.badgeBlocked : isFlag ? styles.badgeFlagged : styles.badgeAllowed;
                    const badgeText = isBlock ? "🚫 BLOCKED" : isFlag ? "⚠️ REVIEW REQUIRED" : "✅ CLEARED";
                    return (
                      <View style={[styles.badge, badgeStyle]}>
                        <Text style={styles.badgeText}>
                          {badgeText}  ·  {Math.round((msg.confidenceScore ?? 0) * 100)}% confidence
                        </Text>
                      </View>
                    );
                  })()}

                  {/* Risk flags */}
                  {msg.riskFlags && msg.riskFlags.length > 0 && (
                    <View style={styles.flagsRow}>
                      {msg.riskFlags.map((f, fi) => (
                        <View key={fi} style={styles.flagPill}>
                          <Text style={styles.flagText}>{f}</Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* AI response or recommendation */}
                  {msg.firewallAction === "block" ? (
                    <Text style={styles.recText}>{msg.recommendation}</Text>
                  ) : msg.content ? (
                    <View style={styles.aiBubble}>
                      <Text style={styles.aiText}>{msg.content}</Text>
                    </View>
                  ) : null}

                  {msg.firewallAction === "override_required" && msg.recommendation && (
                    <Text style={styles.recText}>{msg.recommendation}</Text>
                  )}
                </View>
              </View>
            )}
          </View>
        ))}

        {busy && (
          <View style={styles.aiRow}>
            <Text style={styles.aiAvatar}>🛡️</Text>
            <View style={styles.typingBubble}>
              <ActivityIndicator size="small" color="#6366f1" />
              <Text style={styles.typingText}>Evaluating…</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Input */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Ask a compliance question…"
          placeholderTextColor="rgba(255,255,255,0.3)"
          multiline
          maxLength={500}
          returnKeyType="send"
          onSubmitEditing={() => sendMessage()}
          blurOnSubmit={false}
        />
        <TouchableOpacity style={[styles.sendBtn, (busy || !inputText.trim()) && styles.sendBtnDisabled]} onPress={() => sendMessage()} disabled={busy || !inputText.trim()}>
          <Text style={styles.sendBtnText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0d0e14" },
  categoryBar: { borderBottomWidth: 1, borderBottomColor: "#161824", paddingVertical: 10 },
  categoryScroll: { paddingHorizontal: 14, gap: 8 },
  catPill: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: "#1f2937" },
  catPillActive: { backgroundColor: "rgba(99,102,241,0.12)", borderColor: "#6366f1" },
  catText: { fontSize: 13, color: "rgba(255,255,255,0.45)", fontWeight: "500" },
  catTextActive: { color: "#818cf8" },
  messages: { flex: 1 },
  messagesContent: { padding: 16, gap: 12 },
  intro: { alignItems: "center", paddingVertical: 24 },
  introIcon: { fontSize: 36, marginBottom: 10 },
  introTitle: { fontSize: 16, fontWeight: "700", color: "#fff", marginBottom: 8 },
  introSub: { fontSize: 13, color: "rgba(255,255,255,0.5)", textAlign: "center", lineHeight: 20, marginBottom: 20 },
  scenarioLabel: { fontSize: 11, fontWeight: "700", color: "rgba(255,255,255,0.3)", letterSpacing: 1, marginBottom: 10, alignSelf: "flex-start" },
  scenarioBtn: { width: "100%", backgroundColor: "#161824", borderWidth: 1, borderColor: "#1f2937", borderRadius: 10, padding: 12, marginBottom: 6 },
  scenarioBtnText: { fontSize: 13, color: "rgba(255,255,255,0.6)" },
  userRow: { alignItems: "flex-end" },
  userBubble: { backgroundColor: "rgba(99,102,241,0.12)", borderWidth: 1, borderColor: "rgba(99,102,241,0.25)", borderRadius: 14, padding: 12, maxWidth: "78%" },
  userText: { fontSize: 14, color: "#e0e7ff", lineHeight: 20 },
  aiRow: { flexDirection: "row", gap: 10, alignItems: "flex-start" },
  aiAvatar: { fontSize: 20, marginTop: 2 },
  aiBubbleWrap: { flex: 1, gap: 6 },
  aiBubble: { backgroundColor: "#161824", borderWidth: 1, borderColor: "#1f2937", borderRadius: 14, padding: 12 },
  aiText: { fontSize: 14, color: "rgba(255,255,255,0.85)", lineHeight: 20 },
  badge: { flexDirection: "row", alignItems: "center", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1 },
  badgeBlocked: { backgroundColor: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.2)" },
  badgeFlagged: { backgroundColor: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.2)" },
  badgeAllowed: { backgroundColor: "rgba(34,197,94,0.06)", borderColor: "rgba(34,197,94,0.15)" },
  badgeText: { fontSize: 12, fontWeight: "700", color: "rgba(255,255,255,0.8)" },
  flagsRow: { flexDirection: "row", flexWrap: "wrap", gap: 4 },
  flagPill: { backgroundColor: "rgba(239,68,68,0.08)", borderWidth: 1, borderColor: "rgba(239,68,68,0.15)", borderRadius: 4, paddingHorizontal: 7, paddingVertical: 2 },
  flagText: { fontSize: 11, color: "#fca5a5" },
  recText: { fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 18 },
  typingBubble: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "#161824", borderWidth: 1, borderColor: "#1f2937", borderRadius: 14, padding: 12 },
  typingText: { fontSize: 13, color: "rgba(255,255,255,0.4)" },
  inputRow: { flexDirection: "row", gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: "#161824", alignItems: "flex-end" },
  input: { flex: 1, backgroundColor: "#161824", borderWidth: 1, borderColor: "#1f2937", borderRadius: 12, color: "#fff", fontSize: 14, paddingHorizontal: 14, paddingVertical: 10, maxHeight: 100 },
  sendBtn: { backgroundColor: "#6366f1", borderRadius: 12, paddingHorizontal: 18, paddingVertical: 10 },
  sendBtnDisabled: { opacity: 0.4 },
  sendBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
