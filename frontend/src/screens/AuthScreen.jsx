import { useState } from "react"
import { registerUser, loginUser } from "../api"

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login")
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      if (mode === "login") {
        const res = await loginUser(email, password)
        setLoading(false)
        // Backend returns { access_token, refresh_token, is_admin }
        if (res.access_token) {
          const userName = localStorage.getItem("finfuture_name") || name || "User"
          onAuth(userName, false)
        } else {
          setError("Ошибка входа")
        }
      } else {
        if (!name.trim()) { setLoading(false); return setError("Введите имя") }
        if (password.length < 8) { setLoading(false); return setError("Пароль должен быть не менее 8 символов") }
        const res = await registerUser(email, name, password)
        setLoading(false)
        // Backend returns { access_token, refresh_token, is_admin }
        if (res.access_token) {
          onAuth(name, true)
        } else {
          setError("Ошибка регистрации")
        }
      }
    } catch (err) {
      setLoading(false)
      const msg = err.message || ""
      if (msg.includes("user_already_exists")) setError("Пользователь уже существует")
      else if (msg.includes("invalid_credentials")) setError("Неверная почта или пароль")
      else setError(msg || "Произошла ошибка")
    }
  }

  const quickLogin = async (guestEmail, guestName, guestPassword) => {
    setError("")
    setLoading(true)
    try {
      // Try login first, register if not found
      try {
        const res = await loginUser(guestEmail, guestPassword)
        if (res.access_token) {
          setLoading(false)
          onAuth(guestName, false)
          return
        }
      } catch { /* login attempt failed, proceed to register */ }
      const res = await registerUser(guestEmail, guestName, guestPassword)
      setLoading(false)
      if (res.access_token) {
        onAuth(guestName, true)
      } else {
        setError("Ошибка")
      }
    } catch (err) {
      setLoading(false)
      // If user exists, try login
      try {
        const res = await loginUser(guestEmail, guestPassword)
        if (res.access_token) {
          setLoading(false)
          onAuth(guestName, false)
          return
        }
      } catch { /* login attempt failed, proceed to register */ }
      setError(err.message || "Ошибка")
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* Logo */}
        <div style={s.logo}>
          <img src="/icons/F-Kernel.png" alt="Kernel" style={{ height: 36 }} />
        </div>
        <div style={s.tagline}>Умный финансовый ассистент для управления личными финансами</div>

        <h2 style={s.title}>{mode === "login" ? "Вход" : "Регистрация"}</h2>

        <form onSubmit={handleSubmit} style={s.form}>
          {mode === "register" && (
            <input style={s.input} type="text" placeholder="Имя" value={name}
              onChange={e => setName(e.target.value)} required />
          )}
          <input style={s.input} type="email" placeholder="Почта" value={email}
            onChange={e => setEmail(e.target.value)} required />
          <input style={s.input} type="password" placeholder="Пароль" value={password}
            onChange={e => setPassword(e.target.value)} required />

          {error && <div style={s.error}>{error}</div>}

          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? "..." : mode === "login" ? "Войти" : "Создать аккаунт"}
          </button>
        </form>

        <button style={s.toggle}
          onClick={() => { setMode(m => m === "login" ? "register" : "login"); setError("") }}>
          {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
        </button>

        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button style={{...s.tbankBtn, flex: 1, fontSize: 13}} disabled={loading}
            onClick={() => quickLogin("guest@finfuture.app", "Гость", "Guest@12345")}>
            Войти как гость
          </button>
          <button style={{...s.tbankBtn, flex: 1, fontSize: 13, background: "#1a1a1a", color: "#fff", border: "none"}} disabled={loading}
            onClick={() => quickLogin("admin@finfuture.app", "Админ", "Admin@12345")}>
            Войти как админ
          </button>
        </div>

        {/* Features */}
        <div style={s.features}>
          {[
            { icon: "/icons/free-icon-money-bag-7510557.png", text: "Учёт транзакций" },
            { icon: "/icons/free-icon-robot-14224105.png", text: "AI-советник" },
            { icon: "/icons/free-icon-trophy-1152912.png", text: "Достижения" },
          ].map((f, i) => (
            <div key={i} style={s.feature}>
              <img src={f.icon} alt="" style={{width:20,height:20}} />
              <span>{f.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const s = {
  page: {
    background: "#f6f7f8", display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "100vh", padding: 16, fontFamily: "Inter, sans-serif",
  },
  card: {
    background: "#ffffff", borderRadius: 20, padding: "40px 32px", maxWidth: 420, width: "100%",
    border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  logo: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 8,
  },
  tagline: {
    fontSize: 13, color: "rgba(0,0,0,0.45)", textAlign: "center", marginBottom: 28,
  },
  title: {
    fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 20, textAlign: "center",
  },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  input: {
    padding: "14px 16px", fontSize: 14, borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.12)", outline: "none",
    fontFamily: "Inter, sans-serif", background: "#f6f7f8",
    color: "#1a1a1a",
  },
  error: {
    padding: "10px 14px", borderRadius: 8, background: "rgba(244,67,54,0.08)",
    color: "#f44336", fontSize: 13,
  },
  btn: {
    width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 700,
    borderRadius: 12, background: "#ffdd2d", color: "#1a1a1a", border: "none",
    cursor: "pointer", marginTop: 4, fontFamily: "inherit",
  },
  dividerRow: {
    display: "flex", alignItems: "center", gap: 12, margin: "16px 0",
  },
  dividerLine: {
    flex: 1, height: 1, background: "rgba(0,0,0,0.08)",
  },
  dividerText: {
    fontSize: 12, color: "rgba(0,0,0,0.3)", flexShrink: 0,
  },
  tbankBtn: {
    width: "100%", padding: "13px 0", fontSize: 14, fontWeight: 600,
    borderRadius: 12, background: "#ffffff", color: "#1a1a1a",
    border: "1px solid rgba(0,0,0,0.12)", cursor: "pointer",
    fontFamily: "inherit", display: "flex", alignItems: "center",
    justifyContent: "center", gap: 8, transition: "all 0.2s",
  },
  toggle: {
    width: "100%", padding: "10px 0", fontSize: 13, color: "rgba(0,0,0,0.45)",
    background: "none", border: "none", cursor: "pointer", marginTop: 12,
    fontFamily: "inherit",
  },
  features: {
    display: "flex", justifyContent: "center", gap: 20,
    marginTop: 28, paddingTop: 20, borderTop: "1px solid rgba(0,0,0,0.06)",
  },
  feature: {
    display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
    fontSize: 11, color: "rgba(0,0,0,0.45)", textAlign: "center",
  },
}
