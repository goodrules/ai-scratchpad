import { useAgentChat } from './hooks/useAgentChat';
import { Header } from './components/Header';
import { ChatThread } from './components/ChatThread';
import { ChatInput } from './components/ChatInput';

export function App() {
  const {
    messages,
    status,
    sendMessage,
    loadMockStage,
    loadMockPrd,
    resetSession,
  } = useAgentChat();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Streamlined Top Bar */}
      <Header
        status={status}
        onReset={resetSession}
        onLoadMockStage={loadMockStage}
        onLoadMockPrd={loadMockPrd}
      />

      {/* Main Streamlined Chat Feed */}
      <main className="flex-1 flex flex-col w-full max-w-4xl mx-auto">
        <ChatThread
          messages={messages}
          status={status}
          onDispatchAction={sendMessage}
        />

        {/* Clean Input at Bottom */}
        <ChatInput
          onSendMessage={sendMessage}
          disabled={status === 'streaming'}
        />
      </main>
    </div>
  );
}

export default App;
