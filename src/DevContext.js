import { createContext } from "react"

// Контекст разработчика — доступен всем компонентам
export const DevContext = createContext({ devMode: false, timeOffset: 0, unlockAll: false, aiStatus: "", setAiStatus: () => {} })
