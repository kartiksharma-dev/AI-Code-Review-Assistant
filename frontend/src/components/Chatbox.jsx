import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Maximize2, Minimize2, Sparkles, AlertTriangle, Code, CheckCircle, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import useStore from '../store/useStore';
import { chatWithAI } from '../services/api';
import toast from 'react-hot-toast';

const Chatbox = () => {
  const { 
    isChatOpen, setIsChatOpen, 
    chatHistory, addChatMessage, 
    code, language, analysisResult, activeContext, setActiveContext
  } = useStore();
  
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isLoading]);

  const handleSend = async (customPrompt = null, intent = null) => {
    const textToSend = customPrompt || input;
    if (!textToSend.trim() && !activeContext) return;

    // Add user message to history
    addChatMessage({
      id: Date.now(),
      role: 'user',
      content: textToSend,
      context: activeContext, // Anchor if any
      timestamp: new Date().toISOString()
    });

    setInput('');
    setIsLoading(true);

    try {
      // Build massive context payload
      const payload = {
        prompt: textToSend,
        intent: intent || 'Explain',
        language,
        code,
        issues: analysisResult?.issues || [],
        complexity: analysisResult ? { time: analysisResult.complexity, space: analysisResult.spaceComplexity } : {},
        active_context: activeContext
      };

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const aiResponse = await chatWithAI(payload, { signal: abortControllerRef.current.signal });

      // AI Response schema: { summary, issues_addressed, fixes: [{code, explanation}], reasoning, recommended_action }
      addChatMessage({
        id: Date.now() + 1,
        role: 'ai',
        structuredData: aiResponse,
        timestamp: new Date().toISOString()
      });

      // Clear active context after successful send
      setActiveContext(null);

    } catch (error) {
      if (error.isCanceled) {
        console.log("Request aborted by user.");
        return; // Ignore aborted requests
      }
      toast.error(error.message || 'Chat failed to connect');
      addChatMessage({
        id: Date.now() + 1,
        role: 'ai',
        isError: true,
        content: 'I encountered an error connecting to the intelligence routing engine. Please try again.',
        timestamp: new Date().toISOString()
      });
    } finally {
      setIsLoading(false);
    }
  };

  const QuickActions = () => (
    <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide">
      {[
        { label: 'Explain Code', intent: 'Explain', icon: <Info size={14} /> },
        { label: 'Reduce Complexity', intent: 'Optimize', icon: <Sparkles size={14} /> },
        { label: 'Improve Readability', intent: 'Readability', icon: <CheckCircle size={14} /> },
        { label: 'Fix Issues', intent: 'Fix', icon: <Code size={14} /> }
      ].map(action => (
        <button
          key={action.label}
          onClick={() => handleSend(`Please ${action.label.toLowerCase()}.`, action.intent)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-full whitespace-nowrap transition-colors border border-slate-700"
        >
          {action.icon}
          {action.label}
        </button>
      ))}
    </div>
  );

  const MessageRenderer = ({ msg }) => {
    if (msg.role === 'user') {
      return (
        <div className="flex flex-col items-end mb-4">
          <div className="bg-indigo-600 text-white px-4 py-2 rounded-2xl rounded-br-sm max-w-[85%] shadow-sm">
            <p className="text-sm">{msg.content}</p>
            {msg.context && (
              <div className="mt-2 bg-indigo-700/50 p-2 rounded text-xs border border-indigo-500/30">
                <span className="font-semibold text-indigo-200">Anchored Issue:</span> {msg.context.message}
              </div>
            )}
          </div>
        </div>
      );
    }

    if (msg.isError) {
      return (
        <div className="flex mb-4">
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-2 rounded-2xl rounded-bl-sm max-w-[85%] flex gap-2">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p className="text-sm">{msg.content}</p>
          </div>
        </div>
      );
    }

    // AI Structured Response Rendering
    const { structuredData } = msg;
    if (!structuredData) return null;

    return (
      <div className="flex flex-col items-start mb-6 w-full">
        <div className="flex items-center gap-2 mb-1 px-1 text-slate-400">
          <Sparkles size={14} className="text-indigo-400" />
          <span className="text-xs font-medium">AI Engineering Assistant</span>
        </div>
        
        <div className="bg-slate-800/80 border border-slate-700/50 text-slate-200 px-4 py-3 rounded-2xl rounded-bl-sm w-[95%] shadow-sm">
          {/* Summary */}
          {structuredData.summary && (
            <div className="mb-3 text-sm font-medium text-slate-100">
              {structuredData.summary}
            </div>
          )}

          {/* Reasoning (Markdown) */}
          {structuredData.reasoning && (
            <div className="prose prose-invert prose-sm max-w-none prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({node, inline, className, children, ...props}) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <SyntaxHighlighter
                        {...props}
                        children={String(children).replace(/\n$/, '')}
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        className="rounded-md my-2"
                      />
                    ) : (
                      <code {...props} className="bg-slate-700/50 px-1 py-0.5 rounded text-indigo-300">
                        {children}
                      </code>
                    )
                  }
                }}
              >
                {structuredData.reasoning}
              </ReactMarkdown>
            </div>
          )}

          {/* Fixes / Code Previews */}
          {structuredData.fixes && structuredData.fixes.length > 0 && (
            <div className="mt-4 space-y-3">
              {structuredData.fixes.map((fix, idx) => (
                <div key={idx} className="border border-indigo-500/20 bg-indigo-500/5 rounded-lg overflow-hidden">
                  <div className="bg-indigo-500/10 px-3 py-1.5 border-b border-indigo-500/20 text-xs text-indigo-300 flex justify-between items-center">
                    <span>Suggested Fix Preview</span>
                    <button className="hover:text-white transition-colors" onClick={() => navigator.clipboard.writeText(fix.code)}>Copy</button>
                  </div>
                  <div className="p-3">
                    <SyntaxHighlighter
                      language={language}
                      style={vscDarkPlus}
                      customStyle={{ margin: 0, padding: 0, background: 'transparent' }}
                    >
                      {fix.code}
                    </SyntaxHighlighter>
                    {fix.explanation && (
                      <div className="mt-2 text-xs text-slate-400 pt-2 border-t border-slate-700/50">
                        {fix.explanation}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <AnimatePresence>
        {!isChatOpen && (
          <motion.button
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-6 right-6 z-40 bg-indigo-600 text-white p-4 rounded-full shadow-lg hover:bg-indigo-500 transition-colors border border-indigo-500/50 flex items-center justify-center group"
          >
            <Sparkles size={24} className="group-hover:animate-pulse" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className={`fixed bottom-6 right-6 z-50 flex flex-col bg-slate-900 border border-slate-700 shadow-2xl rounded-2xl overflow-hidden ${
              isExpanded ? 'w-[800px] h-[80vh]' : 'w-[400px] h-[600px]'
            }`}
          >
            {/* Header */}
            <div className="bg-slate-800/80 px-4 py-3 border-b border-slate-700 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-2">
                <div className="bg-indigo-500/20 p-1.5 rounded-lg">
                  <Sparkles size={16} className="text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-200">AI Engineering Assistant</h3>
                  <p className="text-[10px] text-slate-400">Context-Aware Engine</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
                <button 
                  onClick={() => setIsChatOpen(false)}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 scroll-smooth">
              {chatHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                  <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center mb-2">
                    <Sparkles size={28} className="text-indigo-400" />
                  </div>
                  <div>
                    <h4 className="text-slate-200 font-medium mb-1">How can I help engineer this?</h4>
                    <p className="text-xs text-slate-400 max-w-[250px]">
                      I can explain complexity, suggest refactors, or fix semantic drift warnings.
                    </p>
                  </div>
                </div>
              ) : (
                chatHistory.map((msg) => (
                  <MessageRenderer key={msg.id} msg={msg} />
                ))
              )}
              
              {isLoading && (
                <div className="flex items-center gap-2 text-slate-400 p-4">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-xs font-medium ml-2">Engine analyzing context...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-slate-900 border-t border-slate-800 shrink-0">
              {chatHistory.length === 0 && <QuickActions />}
              
              {/* Active Context Anchoring Indicator */}
              <AnimatePresence>
                {activeContext && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: 10, height: 0 }}
                    className="mb-2 bg-indigo-900/30 border border-indigo-500/30 rounded-md px-3 py-2 flex justify-between items-center text-xs"
                  >
                    <div className="flex items-center gap-2 truncate text-indigo-200">
                      <Code size={14} className="shrink-0" />
                      <span className="truncate font-medium">Anchored: {activeContext.message}</span>
                    </div>
                    <button onClick={() => setActiveContext(null)} className="text-indigo-400 hover:text-indigo-200 ml-2">
                      <X size={14} />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Ask about this code..."
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  rows={1}
                  style={{ minHeight: '44px', maxHeight: '120px' }}
                  disabled={isLoading}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={(!input.trim() && !activeContext) || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white rounded-lg transition-colors"
                >
                  <Send size={16} />
                </button>
              </div>
              <div className="text-center mt-2">
                <span className="text-[10px] text-slate-500">AI-assisted deterministic software engineering platform</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default Chatbox;
