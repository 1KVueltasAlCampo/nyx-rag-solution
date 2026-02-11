import { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error("Error connecting to API:", err))
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>NYX RAG Solution</h1>
      <p>Frontend: <strong>Active</strong></p>
      <p>Backend Connection: {health ? <span style={{color: 'green'}}>OK ({health.service})</span> : <span style={{color: 'red'}}>Connecting...</span>}</p>
    </div>
  )
}

export default App