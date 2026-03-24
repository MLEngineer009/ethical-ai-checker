# Ethical AI — iOS App Setup

## Requirements
- Xcode 15+
- iOS 16+ deployment target
- Google Cloud project with OAuth Client ID (same one used by the web app)

---

## Step 1 — Create Xcode Project

1. Open Xcode → **File → New → Project**
2. Choose **iOS → App**
3. Set:
   - Product Name: `EthicalAI`
   - Bundle Identifier: `com.yourname.ethical-ai`
   - Interface: **SwiftUI**
   - Language: **Swift**
4. **Uncheck** "Include Tests"
5. Save it inside this `ios/` folder

---

## Step 2 — Add Swift Source Files

Delete the auto-generated `ContentView.swift`, then drag all files from `EthicalAI/` into the Xcode project:

```
App/
  EthicalAIApp.swift
  ContentView.swift
Models/
  Models.swift
Services/
  AuthState.swift
  APIService.swift
Views/
  BackgroundView.swift
  AuthView.swift
  HomeView.swift
  ResultsView.swift
```

When prompted, check **"Copy items if needed"** and **"Add to target: EthicalAI"**.

---

## Step 3 — Add GoogleSignIn via Swift Package Manager

1. In Xcode: **File → Add Package Dependencies…**
2. Enter URL: `https://github.com/google/GoogleSignIn-iOS`
3. Select version: **Up to Next Major** from `7.0.0`
4. Add **GoogleSignIn** to your target (not GoogleSignInSwift unless needed)

---

## Step 4 — Configure Google Sign-In

In your [Google Cloud Console](https://console.cloud.google.com):

1. Go to **APIs & Services → Credentials**
2. Open your OAuth 2.0 Web Client (created for the web app)
3. Under **Authorized JavaScript origins**, add `http://localhost:8000`
4. Create a **separate iOS OAuth Client**:
   - Application type: **iOS**
   - Bundle ID: `com.yourname.ethical-ai`
5. Copy the **iOS Client ID** and its **Reversed Client ID**
   - iOS Client ID: `123456789-xxx.apps.googleusercontent.com`
   - Reversed Client ID: `com.googleusercontent.apps.123456789-xxx`

Then update two places:

**`AuthView.swift`** line 14:
```swift
private let googleClientID = "YOUR_IOS_CLIENT_ID.apps.googleusercontent.com"
```

**`Resources/Info.plist`** — replace the URL scheme:
```xml
<string>com.googleusercontent.apps.YOUR_REVERSED_CLIENT_ID</string>
```

Replace `Info.plist` in Xcode with the one from `Resources/Info.plist` (or merge the URL scheme entry into your existing one).

---

## Step 5 — Update Backend URL

If testing on a **real device** (not simulator), update `APIService.swift` line 13:

```swift
let baseURL = "http://192.168.1.XXX:8000"  // your Mac's local IP
```

Find your Mac's IP: **System Settings → Wi-Fi → Details → IP Address**

For **simulator**, `localhost:8000` works as-is.

---

## Step 6 — Run

1. Start the backend: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2. Select iPhone simulator in Xcode
3. Press **⌘R**

---

## App Structure

```
EthicalAI/
├── App/
│   ├── EthicalAIApp.swift      Entry point, Google URL handler
│   └── ContentView.swift       Auth routing (login ↔ main app)
├── Models/
│   └── Models.swift            All Codable data models
├── Services/
│   ├── AuthState.swift         Session management (ObservableObject)
│   └── APIService.swift        HTTP client for all backend calls
├── Views/
│   ├── BackgroundView.swift    Animated glassmorphism background
│   ├── AuthView.swift          Google Sign-In + Guest button
│   ├── HomeView.swift          Decision form + context fields
│   └── ResultsView.swift       Accordion analysis + PDF share
└── Resources/
    └── Info.plist              URL schemes, ATS config
```

## Features
- Google SSO or Guest access
- Decision input with dynamic context fields (+ Add Field)
- Glassmorphism dark UI matching the web app
- Accordion framework cards (tap to expand)
- Animated confidence bar
- Risk flag chips
- PDF generation + iOS Share Sheet
- Session persistence (Google sessions survive app restart; guest sessions are ephemeral)
