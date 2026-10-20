import { Navigate, Route, Routes } from "react-router"
import { LoginScreen } from "@/features/auth/LoginScreen"
import { SignupScreen } from "@/features/auth/SignupScreen"
import { useAuth } from "@/features/auth/useAuth"
import { ChatScreen } from "@/features/chat/ChatScreen"

// Which page each address shows (react-router, D7).
// Logged out: / sends you to /login. Logged in: /login and /signup send you to /.
// So logging in, signing up or logging out only has to change the user.
function App() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route path="/" element={user ? <ChatScreen user={user} /> : <Navigate to="/login" replace />} />
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginScreen />} />
      <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignupScreen />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
