import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './index.css';

const BACKEND_URL = "http://localhost:8000";

// A2UI Component Renderer - Renders declarative UI components from JSON
function A2UIRenderer({ components, data }) {
  if (!components || Object.keys(components).length === 0) return null;

  const root = components.root;
  if (!root) return null;

  return (
    <div className="a2ui-surface">
      <RenderComponent comp={root} components={components} data={data} />
    </div>
  );
}

function RenderComponent({ comp, components, data }) {
  const { type, props = {}, children = [], binding } = comp;

  // Resolve data binding for dynamic content
  let boundData = null;
  if (binding && data) {
    const parts = binding.replace(/^\//, '').split('/');
    boundData = parts.reduce((acc, part) => acc?.[part], data);
  }

  // Render children components recursively
  const renderChildren = () =>
    children.map((childId) => {
      const child = components[childId];
      return child ? (
        <RenderComponent key={childId} comp={child} components={components} data={data} />
      ) : null;
    });

  switch (type) {
    case 'container':
      return <div className={`a2ui-container ${props.direction === 'row' ? 'row' : ''}`}>{renderChildren()}</div>;

    case 'card':
      return <div className="a2ui-card">{renderChildren()}</div>;

    case 'text':
      const Tag = props.variant === 'h5' ? 'h2' : props.variant === 'h6' ? 'h3' : 'p';
      return <Tag className="a2ui-text">{props.text}</Tag>;

    case 'markdown':
      return <div className="a2ui-markdown"><ReactMarkdown>{props.text}</ReactMarkdown></div>;

    case 'alert':
      const iconMap = {
        success: '✓',
        warning: '⚠',
        error: '✕',
        info: 'ℹ'
      };
      return (
        <div className={`a2ui-alert a2ui-alert-${props.severity || 'info'}`}>
          <span className="alert-icon">{iconMap[props.severity] || 'ℹ'}</span>
          <div className="alert-content">
            <strong>{props.title}</strong>
            <span>{props.message}</span>
          </div>
        </div>
      );

    case 'table':
      if (!boundData?.headers || !boundData?.rows) {
        return <div className="a2ui-loading">Loading table data...</div>;
      }
      return (
        <div className="a2ui-table-container">
          <table className="a2ui-table">
            <thead>
              <tr>
                {boundData.headers.map((h, i) => <th key={i}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {boundData.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => <td key={j}>{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'progress':
      return <div className="a2ui-progress"><div className="a2ui-progress-bar"></div></div>;

    case 'button':
      return (
        <button className={`a2ui-button ${props.variant === 'contained' ? 'primary' : 'outlined'}`}>
          {props.label}
        </button>
      );

    case 'chip':
      return <span className={`a2ui-chip ${props.color || ''}`}>{props.label}</span>;

    case 'divider':
      return <hr className="a2ui-divider" />;

    case 'list':
      return (
        <ul className="a2ui-list">
          {(boundData || props.items || []).map((item, i) => (
            <li key={i}>{typeof item === 'object' ? item.text : item}</li>
          ))}
        </ul>
      );

    default:
      return <div>{renderChildren()}</div>;
  }
}

// Tool Call Display Component
function ToolCallDisplay({ toolName, args, result, status }) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon = {
    running: '⟳',
    success: '✓',
    error: '✕'
  };

  return (
    <div className={`tool-call ${status}`}>
      <div className="tool-header" onClick={() => setExpanded(!expanded)}>
        <span className="tool-icon">{statusIcon[status] || '•'}</span>
        <span className="tool-name">{toolName}</span>
        <span className="tool-expand">{expanded ? '−' : '+'}</span>
      </div>
      {expanded && (
        <div className="tool-details">
          {args && (
            <div className="tool-args">
              <strong>Arguments:</strong>
              <pre>{JSON.stringify(args, null, 2)}</pre>
            </div>
          )}
          {result && (
            <div className="tool-result">
              <strong>Result:</strong>
              <pre>{typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [a2uiComponents, setA2uiComponents] = useState({});
  const [a2uiData, setA2uiData] = useState({});
  const [toolCalls, setToolCalls] = useState([]);
  const [streamingText, setStreamingText] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText, a2uiComponents]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);
    setA2uiComponents({});
    setA2uiData({});
    setToolCalls([]);
    setStreamingText('');

    try {
      const response = await fetch(`${BACKEND_URL}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: userMessage }],
          extensions: ['a2ui']
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let textContent = '';
      let currentComponents = {};
      let currentData = {};
      let currentToolCalls = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          try {
            const event = JSON.parse(line.slice(6));
            const eventType = event.type;

            if (eventType === 'A2UI_MESSAGE') {
              const a2ui = event.a2ui;
              if (a2ui.type === 'surfaceUpdate') {
                const newComps = {};
                for (const comp of a2ui.components || []) {
                  newComps[comp.id] = comp;
                }
                currentComponents = { ...currentComponents, ...newComps };
                setA2uiComponents({ ...currentComponents });
              } else if (a2ui.type === 'dataModelUpdate') {
                currentData = { ...currentData, ...a2ui.data };
                setA2uiData({ ...currentData });
              }
            } else if (eventType === 'TEXT_MESSAGE_CONTENT') {
              textContent += event.delta || '';
              setStreamingText(textContent);
            } else if (eventType === 'TOOL_CALL_START') {
              currentToolCalls.push({
                id: event.toolCallId,
                name: event.toolName,
                args: null,
                result: null,
                status: 'running'
              });
              setToolCalls([...currentToolCalls]);
            } else if (eventType === 'TOOL_CALL_ARGS') {
              const idx = currentToolCalls.findIndex(t => t.id === event.toolCallId);
              if (idx >= 0) {
                try {
                  currentToolCalls[idx].args = JSON.parse(event.args);
                } catch {
                  currentToolCalls[idx].args = event.args;
                }
                setToolCalls([...currentToolCalls]);
              }
            } else if (eventType === 'TOOL_CALL_END') {
              const idx = currentToolCalls.findIndex(t => t.id === event.toolCallId);
              if (idx >= 0) {
                currentToolCalls[idx].status = 'success';
                currentToolCalls[idx].result = event.result;
                setToolCalls([...currentToolCalls]);
              }
            }
          } catch (e) {
            console.error('Parse error:', e);
          }
        }
      }

      if (textContent) {
        setMessages(prev => [...prev, { role: 'assistant', content: textContent }]);
        setStreamingText('');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: ' + error.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const exampleQueries = [
    { text: "List crashloop pods in staging", icon: "🔄" },
    { text: "Show recent PagerDuty incidents", icon: "🚨" },
    { text: "Check service health metrics", icon: "📊" },
    { text: "Find high memory pods in prod", icon: "💾" }
  ];

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <h1>SRE Copilot</h1>
            <span className="header-tagline">AI-Powered Infrastructure Assistant</span>
          </div>
          <div className="header-right">
            <span className="protocol-badge datadog">Datadog</span>
            <span className="protocol-badge pagerduty">PagerDuty</span>
            <span className="protocol-badge observe">Observe</span>
          </div>
        </div>
      </header>

      <div className="main">
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3>Quick Actions</h3>
            <div className="example-queries">
              {exampleQueries.map((query, i) => (
                <button key={i} onClick={() => setInput(query.text)} className="example-btn">
                  <span className="example-icon">{query.icon}</span>
                  <span className="example-text">{query.text}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <h3>Protocol Stack</h3>
            <div className="stack-info">
              <div className="stack-item">
                <span className="stack-badge green">A2UI</span>
                <span className="stack-desc">Rich UI Components</span>
              </div>
              <div className="stack-item">
                <span className="stack-badge blue">AG-UI</span>
                <span className="stack-desc">SSE Streaming</span>
              </div>
              <div className="stack-item">
                <span className="stack-badge purple">LangGraph</span>
                <span className="stack-desc">Agent Orchestration</span>
              </div>
            </div>
          </div>

          <div className="sidebar-section">
            <h3>Capabilities</h3>
            <ul className="capabilities-list">
              <li>Kubernetes pod monitoring</li>
              <li>Incident management</li>
              <li>Metric analysis</li>
              <li>Log exploration</li>
              <li>Alert correlation</li>
            </ul>
          </div>
        </aside>

        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && !loading && (
              <div className="welcome-message">
                <h2>Welcome to SRE Copilot</h2>
                <p>Ask me about your infrastructure, pods, incidents, or metrics.</p>
                <p className="hint">Try one of the quick actions on the left to get started.</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}

            {/* Streaming text */}
            {streamingText && (
              <div className="message assistant">
                <div className="message-avatar">🤖</div>
                <div className="message-content">
                  <ReactMarkdown>{streamingText}</ReactMarkdown>
                </div>
              </div>
            )}

            {/* Tool calls */}
            {toolCalls.length > 0 && (
              <div className="tool-calls-container">
                <div className="tool-calls-header">Tool Executions</div>
                {toolCalls.map((tc, i) => (
                  <ToolCallDisplay key={i} {...tc} />
                ))}
              </div>
            )}

            {/* A2UI Rich Components */}
            {Object.keys(a2uiComponents).length > 0 && (
              <div className="message assistant a2ui-message">
                <div className="message-avatar">📊</div>
                <div className="message-content">
                  <div className="a2ui-badge">A2UI Rich UI</div>
                  <A2UIRenderer components={a2uiComponents} data={a2uiData} />
                </div>
              </div>
            )}

            {loading && !streamingText && (
              <div className="message assistant loading">
                <div className="message-avatar">🤖</div>
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
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
                onKeyPress={handleKeyPress}
                placeholder="Ask about pods, incidents, metrics..."
                disabled={loading}
              />
              <button onClick={sendMessage} disabled={loading || !input.trim()}>
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
            <div className="input-hint">
              Press Enter to send. Powered by LangGraph + A2UI.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
