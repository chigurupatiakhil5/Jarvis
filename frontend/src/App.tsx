import { useEffect, useState } from 'react'
import './App.css'

interface AgentEvent {
  agent_name: string
  action_type: string
  input: string
  output: string
  status: string
  timestamp: string
}

const API_BASE = 'http://localhost:8001'
const WS_URL = 'ws://localhost:8001/ws'

function App() {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/logs`)
      .then((res) => res.json())
      .then((data: AgentEvent[]) => setEvents(data))
      .catch(() => {})

    const ws = new WebSocket(WS_URL)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (msg) => {
      const event: AgentEvent = JSON.parse(msg.data)
      setEvents((prev) => [...prev, event])
    }

    return () => ws.close()
  }, [])

  return (
    <div className="dashboard">
      <header>
        <h1>Jarvis — Live Agent Activity</h1>
        <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </header>

      <div className="events">
        {events.length === 0 && (
          <p className="empty">No activity yet. Give Jarvis a command.</p>
        )}
        {events
          .slice()
          .reverse()
          .map((event, i) => (
            <div key={i} className={`event ${event.status}`}>
              <div className="event-top">
                <span className="agent">{event.agent_name}</span>
                <span className="action">{event.action_type}</span>
                <span className={`badge ${event.status}`}>{event.status}</span>
                <span className="time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="event-body">
                <div>
                  <strong>In:</strong> {event.input}
                </div>
                <div>
                  <strong>Out:</strong> {event.output}
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}

export default App
