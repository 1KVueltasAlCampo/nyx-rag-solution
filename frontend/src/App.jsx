import { useState, useEffect, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { BookOpen, MessageSquare, Plus, Upload, X, Send, FileText, CheckCircle, AlertCircle } from 'lucide-react'

const API_URL = "http://localhost:8000/api/v1"

function App() {
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [evidence, setEvidence] = useState(null)
  
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)
  const [health, setHealth] = useState("checking")
  const [uploadStatus, setUploadStatus] = useState(null)

  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => res.ok ? setHealth("online") : setHealth("error"))
      .catch(() => setHealth("offline"))

    const saved = localStorage.getItem('nyx_sessions')
    if (saved) {
      const parsed = JSON.parse(saved)
      setSessions(parsed)
      if (parsed.length > 0) {
        selectSession(parsed[0].id)
      } else {
        createNewSession()
      }
    } else {
      createNewSession()
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const createNewSession = () => {
    const newSession = {
      id: uuidv4(),
      name: `Analysis ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`,
      createdAt: new Date()
    }
    const updated = [newSession, ...sessions]
    setSessions(updated)
    localStorage.setItem('nyx_sessions', JSON.stringify(updated))
    selectSession(newSession.id)
  }

  const selectSession = (id) => {
    setCurrentSessionId(id)
    setMessages([])
    setUploadStatus(null)
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMsg = { id: uuidv4(), role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setIsLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: userMsg.content
        })
      })

      if (!res.ok) throw new Error("Failed to fetch")

      const data = await res.json()
      
      const aiMsg = {
        id: uuidv4(),
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        isRefusal: data.is_refusal,
        toolUsed: data.tool_used
      }
      setMessages(prev => [...prev, aiMsg])

    } catch (err) {
      console.error("Chat Error:", err)
      setMessages(prev => [...prev, { 
          id: uuidv4(), 
          role: 'assistant', 
          content: "Error: Could not reach NYX Brain.", 
          isError: true 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setIsUploading(true)
    setUploadStatus(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await fetch(`${API_URL}/documents`, {
        method: 'POST',
        body: formData
      })

      if (!res.ok) throw new Error("Upload failed")
      
      const data = await res.json()
      setUploadStatus(data.status === 'skipped' ? 'duplicate' : 'success')
      
      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: 'system',
        content: `System: Document "${file.name}" processed successfully. (${data.status})`
      }])

    } catch (err) {
      console.error("Upload Error:", err)
      setUploadStatus('error')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleCitationClick = async (citation) => {
    setShowEvidence(true)
    setEvidence({ loading: true, ...citation })

    try {
        const [docId, chunkIndex] = citation.source_id.split('_')
        
        const res = await fetch(`${API_URL}/chunks/${docId}/${chunkIndex}`)
        if (!res.ok) throw new Error("Failed to load chunk")
        
        const data = await res.json()
        setEvidence(prev => ({ ...prev, loading: false, fullText: data.content }))

    } catch (err) {
        console.error("Evidence Error:", err)
        setEvidence(prev => ({ ...prev, loading: false, fullText: "Error loading source text." }))
    }
  }

  return (
    <div className="app-container">
      
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: 0, fontSize: '1.2rem' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: health === 'online' ? 'var(--success)' : 'var(--danger)', boxShadow: `0 0 10px ${health === 'online' ? 'var(--success)' : 'var(--danger)'}` }} />
            NYX Console
          </h2>
        </div>

        <button onClick={createNewSession} className="btn-primary" style={{ marginBottom: '1.5rem', width: '100%', justifyContent: 'center' }}>
          <Plus size={18} /> New Analysis
        </button>

        <div className="session-list">
          <h3 style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '10px' }}>History</h3>
          {sessions.map(s => (
            /* S1082 & S6848 Fix: Changed div to button for accessibility */
            <button 
              key={s.id}
              onClick={() => selectSession(s.id)}
              className={`session-item ${s.id === currentSessionId ? 'active' : ''}`}
              style={{
                  width: '100%',
                  background: 'none',
                  border: 'none',
                  textAlign: 'left',
                  fontFamily: 'inherit'
              }}
            >
              <MessageSquare size={14} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</span>
            </button>
          ))}
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
            <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
                style={{ display: 'none' }} 
                accept=".pdf,.txt,.md"
            />
            <button 
                onClick={() => fileInputRef.current.click()}
                className="btn-secondary"
                style={{ width: '100%', justifyContent: 'center', position: 'relative' }}
                disabled={isUploading}
            >
                {isUploading ? (
                    <span>Uploading...</span>
                ) : (
                    <>
                        <Upload size={16} /> Upload Context
                        {uploadStatus === 'success' && <CheckCircle size={16} style={{ color: 'var(--success)', position: 'absolute', right: 10 }} />}
                        {uploadStatus === 'error' && <AlertCircle size={16} style={{ color: 'var(--danger)', position: 'absolute', right: 10 }} />}
                    </>
                )}
            </button>
        </div>
      </aside>

      {/* CHAT AREA */}
      <main className="chat-area">
        <header style={{ padding: '1rem 2rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(10px)', zIndex: 5 }}>
            <div>
                <strong style={{ display: 'block', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>SESSION ID</strong>
                <span style={{ fontFamily: 'monospace', fontSize: '1.1rem' }}>{currentSessionId?.slice(0, 8)}...</span>
            </div>
            {evidence && (
                <button 
                    onClick={() => setShowEvidence(!showEvidence)}
                    className="btn-secondary"
                >
                    {showEvidence ? 'Hide Inspector' : 'Show Inspector'}
                </button>
            )}
        </header>

        <div className="messages-container">
            {messages.length === 0 && (
                <div className="empty-state">
                    <div className="logo-placeholder">NYX</div>
                    <p>AI Retrieval Augmented Generation System</p>
                    <small>Upload a document to start extracting intelligence.</small>
                </div>
            )}
            
            {messages.map((msg) => (
                /* S6479 Fix: Use unique ID instead of index */
                <div key={msg.id} className={`message ${msg.role}`}>
                    <div className="bubble">
                        {msg.content}
                        
                        {msg.citations && msg.citations.length > 0 && (
                            <div className="citations-wrapper">
                                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', marginRight: 5, color: 'var(--text-secondary)' }}>SOURCES:</span>
                                {msg.citations.map((cit, cIdx) => (
                                    /* S6479 Fix: Use combined key (file+chunk) instead of index, or index if necessary but stable */
                                    <button 
                                        key={`${cit.source_id}-${cIdx}`} 
                                        className="citation-chip"
                                        onClick={() => handleCitationClick(cit)}
                                    >
                                        {cit.file_name.slice(0, 10)}... (p.{cit.page})
                                    </button>
                                ))}
                            </div>
                        )}
                        
                        {msg.toolUsed && (
                            <div style={{ marginTop: 5, fontSize: '0.7rem', opacity: 0.5, fontStyle: 'italic' }}>
                                Tool: {msg.toolUsed}
                            </div>
                        )}
                    </div>
                </div>
            ))}
            
            {isLoading && (
                <div className="message assistant">
                    <div className="bubble typing">Thinking...</div>
                </div>
            )}
            <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
            <div className="input-wrapper">
                <input 
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Ask a question..." 
                    disabled={isLoading}
                />
                <button onClick={handleSend} disabled={isLoading || !input.trim()}>
                    <Send size={18} />
                </button>
            </div>
        </div>
      </main>

      {/* EVIDENCE PANEL */}
      <aside className={`evidence-panel ${showEvidence ? 'open' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Evidence Inspector</h3>
            <button onClick={() => setShowEvidence(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}><X size={20}/></button>
        </div>
        
        {evidence ? (
            <div>
                <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Source File</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 'bold' }}>
                        <FileText size={16} color="var(--accent)" />
                        {evidence.file_name}
                    </div>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Page</div>
                    <div>{evidence.page}</div>
                </div>

                <div style={{ marginTop: '2rem' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 5 }}>Raw Content Chunk</div>
                    <div className="evidence-content">
                        {evidence.loading ? (
                            <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>Loading raw text from Vector DB...</span>
                        ) : (
                            evidence.fullText
                        )}
                    </div>
                </div>
            </div>
        ) : (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textAlign: 'center', marginTop: '4rem' }}>
                <BookOpen size={40} style={{ display: 'block', margin: '0 auto 1rem', opacity: 0.3 }} />
                Select a citation in the chat to verify the source truth.
            </div>
        )}
      </aside>

    </div>
  )
}

export default App