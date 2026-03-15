import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import {
  Globe, Atom, Code, Send, Paperclip, Microscope,
  X, FileText, Loader2, Play, Database, RotateCcw, Folder, Square
} from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// Configuració visual per cada mode
const MODE_CONFIG = {
  general:     { label: 'General',     Icon: Globe, accent: '#0284c7', dim: '#0c2233' },
  science:     { label: 'Ciència',     Icon: Atom,  accent: '#16a34a', dim: '#0a1f10' },
  programming: { label: 'Programació', Icon: Code,        accent: '#dc2626', dim: '#1f0a0a' },
  research:     { label: 'Investigació', Icon: Microscope, accent: '#6d28d9', dim: '#12091f' },
};

function App() {
  const [mode, setMode] = useState('general');
  const [images, setImages] = useState([]); // fins a 5 imatges
  const [documents, setDocuments] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sandboxEnvCount, setSandboxEnvCount] = useState(0);
  const [userScrolled, setUserScrolled] = useState(false);

  // 🛑 BOTÓ STOP - Nous estats
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentController, setCurrentController] = useState(null);

  // 3 converses independents — cada mode té els seus missatges, input i resultats de lab
  const [conversations, setConversations] = useState({
    general:     { messages: [], input: '', labResults: {} },
    science:     { messages: [], input: '', labResults: {} },
    programming: { messages: [], input: '', labResults: {} },
    research:     { messages: [], input: '', labResults: {} },
  });

  const fileInputRef         = useRef(null);
  const messagesEndRef       = useRef(null);
  const messagesContainerRef = useRef(null);

  // Shortcuts per la conversa activa
  const conv       = conversations[mode];
  const messages   = conv.messages;
  const input      = conv.input;
  const labResults = conv.labResults;

  const setMessages = (updater) => setConversations(prev => ({
    ...prev,
    [mode]: {
      ...prev[mode],
      messages: typeof updater === 'function' ? updater(prev[mode].messages) : updater
    }
  }));

  const setInput = (val) => setConversations(prev => ({
    ...prev,
    [mode]: { ...prev[mode], input: val }
  }));

  const setLabResults = (updater) => setConversations(prev => ({
    ...prev,
    [mode]: {
      ...prev[mode],
      labResults: typeof updater === 'function' ? updater(prev[mode].labResults) : updater
    }
  }));

  const accent = MODE_CONFIG[mode].accent;
  const dim    = MODE_CONFIG[mode].dim;

  // ---------------------------------------------------------------------------
  // Scroll
  // ---------------------------------------------------------------------------

  const scrollToBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container || userScrolled) return;
    container.scrollTop = container.scrollHeight;
  }, [userScrolled]);

  useEffect(() => {
    scrollToBottom();
  }, [isThinking, scrollToBottom]);

  // Reset scroll quan canviem de mode
  useEffect(() => {
    setUserScrolled(false);
    setTimeout(() => {
      const container = messagesContainerRef.current;
      if (container) container.scrollTop = container.scrollHeight;
    }, 50);
  }, [mode]);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    setUserScrolled(!isAtBottom);
  };

  // ---------------------------------------------------------------------------
  // Documents
  // ---------------------------------------------------------------------------

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/api/documents`);
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error("Error carregant documents", err);
    }
  }, []); // eslint-disable-line

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.type.startsWith('image/')) {
      if (images.length >= 5) { alert("Màxim 5 imatges per missatge."); return; }
      const reader = new FileReader();
      reader.onloadend = () => setImages(prev => [...prev, reader.result.split(',')[1]]);
      reader.readAsDataURL(file);
    } else if (
      file.type === 'application/pdf' ||
      file.name.endsWith('.docx') ||
      file.name.endsWith('.csv') ||
      file.name.endsWith('.txt') ||
      file.name.endsWith('.md')
    ) {
      const formData = new FormData();
      formData.append('file', file);
      setIsThinking(true);
      try {
        await axios.post(`${API_URL}/api/upload`, formData);
        await fetchDocuments();
        setImages([]);
      } catch (err) {
        alert("Error al carregar document al motor RAG");
      } finally {
        setIsThinking(false);
      }
    }
    e.target.value = null;
  };

  const handleDeleteDocument = async (filename) => {
    try {
      await axios.delete(`${API_URL}/api/documents/${encodeURIComponent(filename)}`);
      await fetchDocuments();
    } catch (err) {
      alert(`Error en esborrar: ${filename}`);
    }
  };

  // ---------------------------------------------------------------------------
  // Laboratori
  // ---------------------------------------------------------------------------

  const runLabExperiment = async (pythonCode, resultKey) => {
    setIsThinking(true);
    try {
      const res = await axios.post(`${API_URL}/api/lab/execute`, { code: pythonCode });
      if (res.data.status === "success") {
        setLabResults(prev => ({
          ...prev,
          [resultKey]: {
            plot:   res.data.plot   || null,
            output: res.data.output || null,
            table:  res.data.table  || null,
          }
        }));
        setSandboxEnvCount(prev => prev + 1);
      } else {
        alert("Error al Sandbox:\n" + res.data.message);
      }
    } catch (err) {
      console.error("Error al laboratori:", err);
    } finally {
      setIsThinking(false);
    }
  };

  const handleResetSandbox = async () => {
    if (!window.confirm("Segur que vols reiniciar el kernel? Totes les variables es perdran.")) return;
    try {
      await axios.post(`${API_URL}/api/lab/reset`);
      setLabResults({});
      setSandboxEnvCount(0);
      alert("Kernel reiniciat correctament.");
    } catch (err) {
      alert("Error en reiniciar el sandbox.");
    }
  };

  const handleDownloadPlot = (plot) => {
    if (!plot) return;
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${plot}`;
    link.download = 'arrel_ai_plot.png';
    link.click();
  };

  const handleDownloadCSV = (tableData) => {
    if (!tableData || tableData.length === 0) return;
    const headers = Object.keys(tableData[0]).join(',');
    const rows = tableData.map(row =>
      Object.values(row).map(val => `"${val !== null ? val : ''}"`).join(',')
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join('\n');
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", "arrel_ai_dades.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const closeLabResult = (resultKey) => {
    setLabResults(prev => {
      const updated = { ...prev };
      delete updated[resultKey];
      return updated;
    });
  };

  // ---------------------------------------------------------------------------
  // Chat
  // ---------------------------------------------------------------------------

  const sendMessage = async () => {
    if (!input.trim() && images.length === 0) return;

    // 🛑 Crear AbortController per poder cancel·lar
    const controller = new AbortController();
    setCurrentController(controller);
    setIsGenerating(true);

    const userMsg      = { role: 'user', content: input, hasImage: images.length > 0 };
    const currentInput = input;
    const currentImages = images;
    const currentMode  = mode;

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setImages([]);
    setIsThinking(true);
    setUserScrolled(false);

    const history = messages.map(m => ({ role: m.role, content: m.content }));

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt:  currentInput,
          images:  currentImages,
          mode:    currentMode,
          history: history,
          research_mode: currentMode === 'research',
        }),
        signal: controller.signal  // 🛑 CRÍTIC: Permet cancel·lar
      });

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantText = '';
      let isFirstChunk  = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        assistantText += decoder.decode(value);

        if (isFirstChunk) {
          setConversations(prev => ({
            ...prev,
            [currentMode]: {
              ...prev[currentMode],
              messages: [...prev[currentMode].messages, { role: 'assistant', content: '' }]
            }
          }));
          isFirstChunk = false;
        }

        const afterSources = assistantText.split('\n\n').slice(1).join('').trim();
        if (afterSources.length > 10) {
          setIsThinking(false);
        }

        setConversations(prev => {
          const msgs = [...prev[currentMode].messages];
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: assistantText };
          return { ...prev, [currentMode]: { ...prev[currentMode], messages: msgs } };
        });
      }

      setIsThinking(false);

    } catch (error) {
      if (error.name === 'AbortError') {
        // 🛑 L'usuari ha fet STOP
        console.log('Generation stopped by user');
        
        setConversations(prev => {
          const msgs = [...prev[currentMode].messages];
          const lastMessage = msgs[msgs.length - 1];
          
          if (lastMessage?.role === 'assistant') {
            // Només afegir si no hi és ja (evitar duplicats)
            if (!lastMessage.content.includes('[Generation stopped by user]')) {
              lastMessage.content += '\n\n**[Generation stopped by user]**';
            }
          } else {
            msgs.push({ 
              role: 'assistant', 
              content: '**[Generation stopped by user]**' 
            });
          }
          
          return { ...prev, [currentMode]: { ...prev[currentMode], messages: msgs } };
        });
        
      } else {
        console.error("Error en el flux:", error);
        setConversations(prev => {
          const msgs = [...prev[currentMode].messages];
          msgs.push({ role: 'assistant', content: `**Error:** ${error.message}` });
          return { ...prev, [currentMode]: { ...prev[currentMode], messages: msgs } };
        });
      }
      
      // Neteja delegada al finally
      
    } finally {
      // 🛑 Neteja COMPLETA de tots els estats
      setIsThinking(false);      // CRÍTIC: Resetar spinner
      setIsGenerating(false);
      setCurrentController(null);
    }
  };

  // 🛑 Funció per aturar la generació
  const stopGeneration = () => {
    if (currentController) {
      currentController.abort();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearConversation = () => {
    setConversations(prev => ({
      ...prev,
      [mode]: { messages: [], input: '', labResults: {} }
    }));
    setUserScrolled(false);
  };

  // ---------------------------------------------------------------------------
  // Component LabWindow inline
  // ---------------------------------------------------------------------------

  const LabWindow = ({ resultKey }) => {
    const result = labResults[resultKey];
    if (!result) return null;
    return (
      <div className="plot-window" style={{ marginTop: '12px', borderColor: accent + '66' }}>
        <div className="plot-header" style={{ backgroundColor: dim, color: accent }}>
          <span>🔬 Resultat del Laboratori</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {result.plot && (
              <button
                onClick={() => handleDownloadPlot(result.plot)}
                className="download-plot-btn"
                style={{ backgroundColor: accent }}
              >
                📥 PNG
              </button>
            )}
            <X size={18} onClick={() => closeLabResult(resultKey)} style={{ cursor: 'pointer' }} />
          </div>
        </div>

        {result.plot && (
          <img src={`data:image/png;base64,${result.plot}`} alt="Gràfic científic" />
        )}

        {result.output && result.output.trim() !== '' && (
          <div className="lab-console">
            <div className="lab-console-header">🖥️ Sortida Estàndard</div>
            <pre>{result.output}</pre>
          </div>
        )}

        {result.table && result.table.length > 0 && (
          <div className="lab-table-container">
            <div className="lab-console-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>📊 DataFrame</span>
              <button
                onClick={() => handleDownloadCSV(result.table)}
                className="download-plot-btn"
                style={{ backgroundColor: accent }}
              >
                📥 CSV
              </button>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>{Object.keys(result.table[0]).map(key => <th key={key} style={{ color: accent }}>{key}</th>)}</tr>
                </thead>
                <tbody>
                  {result.table.slice(0, 100).map((row, ri) => (
                    <tr key={ri}>
                      {Object.values(row).map((val, j) => (
                        <td key={j}>{val !== null ? val.toString() : 'NaN'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.table.length > 100 && (
                <div className="table-footer">Mostrant 100 de {result.table.length} files.</div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="app-container">
      {/* ---- SIDEBAR ---- */}
      <div className="sidebar">
        <h1 style={{ color: accent }}>Arrel AI</h1>

        <div className="sidebar-section">
          <div className="section-label">Mode</div>
          {Object.entries(MODE_CONFIG).map(([key, cfg]) => {
            const hasMessages = conversations[key].messages.length > 0;
            return (
              <button
                key={key}
                className={`mode-btn ${mode === key ? 'active' : ''}`}
                style={mode === key ? { backgroundColor: cfg.accent } : {}}
                onClick={() => setMode(key)}
              >
                <cfg.Icon size={18} />
                {cfg.label}
                {/* Punt indicador de conversa activa en altres modes */}
                {hasMessages && mode !== key && (
                  <span className="conv-dot" style={{ backgroundColor: cfg.accent }} />
                )}
              </button>
            );
          })}
        </div>

        <div className="sidebar-section">
          <div className="section-label">Laboratori</div>
          <button className="mode-btn reset-btn" onClick={handleResetSandbox}>
            <RotateCcw size={18} /> Reset Kernel
            {sandboxEnvCount > 0 && (
              <span className="env-badge" style={{ backgroundColor: accent }}>
                {sandboxEnvCount}
              </span>
            )}
          </button>
        </div>

        <div className="sidebar-section docs-section">
          <div className="section-label">
            <Database size={12} style={{ display: 'inline', marginRight: 4 }} />
            Memòria RAG
          </div>

          <div className="watch-folder-hint">
            <Folder size={12} />
            <span>Posa fitxers a <code>~/Arrel_AI</code> per indexar-los automàticament</span>
          </div>

          {documents.length === 0 ? (
            <div className="empty-docs">Cap document indexat.</div>
          ) : (
            <div className="docs-list">
              {documents.map((doc, idx) => (
                <div key={idx} className="doc-indicator" style={{ borderColor: accent + '44' }}>
                  <div className="doc-indicator-name" title={doc}>
                    <FileText size={13} style={{ flexShrink: 0, color: accent }} />
                    <span>{doc.length > 22 ? doc.substring(0, 20) + '...' : doc}</span>
                  </div>
                  <X size={15} className="delete-doc-btn" onClick={() => handleDeleteDocument(doc)} />
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="mode-btn clear-btn" onClick={clearConversation} style={{ marginTop: 'auto' }}>
          <RotateCcw size={18} /> Nova conversa
        </button>
      </div>

      {/* ---- CHAT AREA ---- */}
      <div className="chat-area" style={{ borderLeft: `2px solid ${accent}33` }}>

        {/* Barra superior del mode actiu */}
        <div className="mode-bar" style={{ backgroundColor: dim, borderBottom: `1px solid ${accent}44` }}>
          {React.createElement(MODE_CONFIG[mode].Icon, { size: 15, color: accent })}
          <span style={{ color: accent, fontWeight: 'bold', fontSize: '0.85rem' }}>
            {MODE_CONFIG[mode].label}
          </span>
          <span style={{ color: accent + '66', fontSize: '0.75rem', marginLeft: 'auto' }}>
            {messages.length > 0 ? `${messages.length} missatges` : 'Conversa nova'}
          </span>
        </div>

        <div
          className="messages"
          ref={messagesContainerRef}
          onScroll={handleScroll}
        >
          {messages.length === 0 && (
            <div className="welcome-screen">
              <div style={{ color: accent, marginBottom: '16px' }}>
                {React.createElement(MODE_CONFIG[mode].Icon, { size: 48 })}
              </div>
              <h2 style={{ color: accent }}>{MODE_CONFIG[mode].label}</h2>
              <p>Conversa independent per cada mode.</p>
              <p className="welcome-hint">
                Posa fitxers a <code style={{ color: accent }}>~/Arrel_AI</code> per usar-los com a context.
              </p>
            </div>
          )}

          {messages.map((m, msgIdx) => {
            // Comptador de blocs de codi per assignar resultKeys inline
            let codeBlockCounter = 0;

            // Renderer personalitzat: injecta el boto just sota cada bloc python
            const CodeRenderer = ({ children, className }) => {
              const isP = className === 'language-python';
              if (isP) {
                const code = String(children).replace(/\n$/, '');
                const currentIdx = codeBlockCounter++;
                const resultKey = `${msgIdx}_${currentIdx}`;
                return (
                  <div>
                    <pre><code className={className}>{children}</code></pre>
                    <button
                      className="run-btn"
                      style={{ backgroundColor: accent }}
                      onClick={() => runLabExperiment(code, resultKey)}
                      key={resultKey}
                    >
                      ▶ Executar al Laboratori
                    </button>
                    <LabWindow resultKey={resultKey} />
                  </div>
                );
              }
              return <code className={className}>{children}</code>;
            };

            return (
              <div key={msgIdx}>
                <div
                  className={`message ${m.role}`}
                  style={m.role === 'user' ? { borderColor: accent + '44', backgroundColor: dim } : {}}
                >
                  {m.hasImage && <div className="image-tag" style={{ color: accent }}>📷 Imatge adjunta</div>}
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{ code: CodeRenderer }}
                  >
                    {m.content}
                  </ReactMarkdown>
                </div>
              </div>
            );
          })}

          {isThinking && (
            <div className="thinking-container pulse">
              <Loader2 className="spinner" size={18} style={{ color: accent }} />
              <span style={{ color: accent + 'aa' }}>Arrel AI està processant...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ---- INPUT ---- */}
        <div className="input-area">
          {images.length > 0 && (
            <div className="image-preview">
              {images.map((img, idx) => (
                <div key={idx} className="image-chip">
                  <img src={`data:image/jpeg;base64,${img}`} alt={`img ${idx+1}`} className="image-thumb" />
                  <X size={12} onClick={() => setImages(prev => prev.filter((_, i) => i !== idx))} style={{ cursor: 'pointer' }} />
                </div>
              ))}
              {images.length < 5 && (
                <span className="image-add-hint">+ pots afegir {5 - images.length} més</span>
              )}
            </div>
          )}
          <div className="input-container" style={{ borderColor: accent + '66' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Missatge a ${MODE_CONFIG[mode].label}... [Enter enviar, Shift+Enter nova línia]`}
              disabled={isGenerating}  // 🛑 Deshabilitar mentre genera
              rows={1}
            />
            <button 
              className="icon-btn" 
              onClick={() => fileInputRef.current.click()} 
              disabled={isGenerating}  // 🛑 Deshabilitar mentre genera
            >
              <Paperclip size={20} />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={handleFileChange}
              accept="image/*,.pdf,.docx,.csv,.txt,.md"
              multiple
            />
            
            {/* 🛑 BOTÓ CONDICIONAL: STOP vs SEND */}
            {isGenerating ? (
              <button
                className="stop-btn"
                onClick={stopGeneration}
                title="Atura la generació"
              >
                <Square size={20} fill="currentColor" />
              </button>
            ) : (
              <button
                className="send-btn"
                style={{ backgroundColor: accent }}
                onClick={sendMessage}
                disabled={!input.trim() && images.length === 0}
              >
                <Send size={20} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;