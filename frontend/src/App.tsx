import { useState } from "react"
import { LoginScreen } from "@/features/auth/LoginScreen"
import { SignupScreen } from "@/features/auth/SignupScreen"
import { ChatScreen } from "@/features/chat/ChatScreen"

type Screen = "login" | "signup" | "chat"

// Picks which screen shows. Plain state, no routing library yet (decided in T12).
// Nothing is saved, so a page reload starts at log-in again.
function App() {
  const [screen, setScreen] = useState<Screen>("login")

  if (screen === "chat") {
    return <ChatScreen onLogout={() => setScreen("login")} />
  }
  if (screen === "signup") {
    return <SignupScreen onSignup={() => setScreen("chat")} onSwitch={() => setScreen("login")} />
  }
  return <LoginScreen onLogin={() => setScreen("chat")} onSwitch={() => setScreen("signup")} />
}

export default App
