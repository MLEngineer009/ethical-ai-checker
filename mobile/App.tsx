import React from "react";
import { ActivityIndicator, View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { AuthProvider, useAuth } from "./src/context/AuthContext";
import { AuthScreen } from "./src/screens/AuthScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { ResultsScreen } from "./src/screens/ResultsScreen";
import { HistoryScreen } from "./src/screens/HistoryScreen";
import { ChatScreen } from "./src/screens/ChatScreen";
import { EthicalAnalysis } from "./src/services/api";

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  Results: {
    analysis: EthicalAnalysis;
    decision: string;
    context: Record<string, string>;
  };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

// ── Simple bottom tab bar ─────────────────────────────────────────────────────

type Tab = "evaluate" | "history" | "chat";

function TabBar({ active, onSwitch }: { active: Tab; onSwitch: (t: Tab) => void }) {
  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "evaluate", label: "Evaluate", icon: "⚖️" },
    { key: "history",  label: "History",  icon: "📋" },
    { key: "chat",     label: "Chat",     icon: "💬" },
  ];
  return (
    <View style={tabStyles.bar}>
      {tabs.map(t => (
        <TouchableOpacity key={t.key} style={tabStyles.tab} onPress={() => onSwitch(t.key)} activeOpacity={0.75}>
          <Text style={tabStyles.icon}>{t.icon}</Text>
          <Text style={[tabStyles.label, active === t.key && tabStyles.labelActive]}>{t.label}</Text>
          {active === t.key && <View style={tabStyles.dot} />}
        </TouchableOpacity>
      ))}
    </View>
  );
}

const tabStyles = StyleSheet.create({
  bar: {
    flexDirection: "row", backgroundColor: "rgba(15,12,41,0.97)",
    borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.1)",
    paddingBottom: 24, paddingTop: 10,
  },
  tab: { flex: 1, alignItems: "center", gap: 3 },
  icon: { fontSize: 20 },
  label: { fontSize: 11, fontWeight: "600", color: "rgba(255,255,255,0.4)" },
  labelActive: { color: "#a78bfa" },
  dot: { width: 4, height: 4, borderRadius: 2, backgroundColor: "#a78bfa", marginTop: 2 },
});

// ── Main tabbed screen ────────────────────────────────────────────────────────

function MainScreen({ navigation }: any) {
  const [activeTab, setActiveTab] = React.useState<Tab>("evaluate");
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flex: 1 }}>
        {activeTab === "evaluate" ? (
          <HomeScreen navigation={navigation} />
        ) : activeTab === "chat" ? (
          <ChatScreen />
        ) : (
          <HistoryScreen />
        )}
      </View>
      <TabBar active={activeTab} onSwitch={setActiveTab} />
    </View>
  );
}

// ── Navigator ─────────────────────────────────────────────────────────────────

function AppNavigator() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f0c29" }}>
        <ActivityIndicator size="large" color="#a78bfa" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: "fade" }}>
        {user ? (
          <>
            <Stack.Screen name="Main" component={MainScreen} />
            <Stack.Screen
              name="Results"
              component={ResultsScreen}
              options={{
                headerShown: true,
                title: "Analysis",
                headerStyle: { backgroundColor: "#0f0c29" },
                headerTintColor: "#a78bfa",
                headerBackTitle: "Back",
              }}
            />
          </>
        ) : (
          <Stack.Screen name="Auth" component={AuthScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppNavigator />
    </AuthProvider>
  );
}
