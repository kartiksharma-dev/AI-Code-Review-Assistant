import { useEffect, useRef, useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import Sidebar from '../components/Sidebar';
import AnalysisPanel from '../components/AnalysisPanel';
import useStore from '../store/useStore';
import { analyzeCode } from '../services/api';
import Chatbox from '../components/Chatbox';

let isPythonIntellisenseRegistered = false;

const Dashboard = () => {
  const { code, setCode, language, setLanguage, analysisResult, setAnalysisResult, setIsAnalyzing, isAnalyzing, addToHistory, setAiError, setAiState, setLastAnalysisTime } = useStore();
  const editorRef = useRef(null);
  const debounceRef = useRef(null);
  const abortRef = useRef(null);
  const requestIdRef = useRef(0);
  const lastCodeRef = useRef("");
  const decorationsCollectionRef = useRef(null);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
  };

  // Sync external code changes (like history clicks or resets) into Monaco
  // This prevents cursor jumping during active typing because it only updates
  // if the editor's internal state doesn't match the Zustand store.
  useEffect(() => {
    if (editorRef.current) {
      const currentEditorCode = editorRef.current.getValue();
      if (currentEditorCode !== code) {
        editorRef.current.setValue(code);
      }
    }
  }, [code]);

  const handleEditorBeforeMount = (monaco) => {
    if (isPythonIntellisenseRegistered) return;
    
    monaco.languages.registerCompletionItemProvider('python', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const keywords = ['print', 'def', 'class', 'import', 'for', 'while', 'if', 'else', 'elif', 'try', 'except', 'return', 'len', 'range', 'input'];
        
        const suggestions = [
          ...keywords.map(kw => ({
            label: kw,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: kw,
            range
          })),
          {
            label: 'for loop',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'for ${1:item} in ${2:iterable}:\n\t${3:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'For Loop',
            range
          },
          {
            label: 'for range',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'for ${1:i} in range(${2:n}):\n\t${3:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'For Range Loop',
            range
          },
          {
            label: 'def function',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'def ${1:function_name}(${2:args}):\n\t${3:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Function Definition',
            range
          },
          {
            label: 'class definition',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'class ${1:ClassName}:\n\tdef __init__(self, ${2:args}):\n\t\t${3:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Class Definition',
            range
          },
          {
            label: 'try/except',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'try:\n\t${1:pass}\nexcept ${2:Exception} as ${3:e}:\n\t${4:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Try/Except Block',
            range
          },
          {
            label: 'if statement',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: 'if ${1:condition}:\n\t${2:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'If Statement',
            range
          }
        ];

        return { suggestions };
      }
    });

    isPythonIntellisenseRegistered = true;
  };

  const runAnalysis = async (currentCode = code) => {
    const trimmedCode = currentCode.trim();
    if (!trimmedCode) {
      setIsAnalyzing(false);
      return;
    }

    const placeholders = [
      "// Write your code here...",
      "# Write your code here...",
      "/* Write your code here... */"
    ];
    if (placeholders.includes(trimmedCode)) {
      setIsAnalyzing(false);
      return;
    }

    if (currentCode === lastCodeRef.current) return;
    lastCodeRef.current = currentCode;

    if (abortRef.current) {
      abortRef.current.abort();
    }
    
    abortRef.current = new AbortController();
    const requestId = ++requestIdRef.current;
    
    setIsAnalyzing(true);
    setAiState('analyzing');
    setAiError(null);

    try {
      const result = await analyzeCode(currentCode, language, {
        signal: abortRef.current.signal
      });
      
      if (requestId !== requestIdRef.current) return;
      
      setAnalysisResult(result);
      addToHistory({
        id: Date.now(),
        codeSnippet: currentCode.slice(0, 100) + '...',
        language,
        score: result.score,
        date: new Date().toISOString()
      });
      setAiState('safe');
      setLastAnalysisTime(new Date());

      // Markers and heatmaps are now handled by a dedicated useEffect to ensure proper cleanup and mapping
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') return;
      
      let finalError = {
         code: 'UNKNOWN_ERROR',
         message: 'Analysis failed. Please check your connection.',
         recoverable: true,
         severity: 'danger'
      };

      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
         finalError = { code: 'TIMEOUT', message: 'Request timed out. Please try again.', recoverable: true, severity: 'warning' };
      } else if (err.response?.data?.error) {
         const be = err.response.data.error;
         if (typeof be === 'object') {
             finalError = { ...finalError, ...be };
         } else {
             finalError.message = be;
         }
      }

      setAiError(finalError);
      setAiState('failed');
    } finally {
      if (requestId === requestIdRef.current) {
        setIsAnalyzing(false);
      }
    }
  };

  const handleAnalyze = () => {
    clearTimeout(debounceRef.current);
    runAnalysis();
  };

  const handleChange = (value) => {
    const newCode = value || "";
    setCode(newCode);

    clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      runAnalysis(newCode);
    }, 700);
  };

  // Keyboard shortcut Ctrl + Enter
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        handleAnalyze();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [code, language, isAnalyzing]); // eslint-disable-line

  useEffect(() => {
    return () => clearTimeout(debounceRef.current);
  }, []);

  // Global Hover Provider Registration
  useEffect(() => {
    const monaco = window.monaco;
    if (!monaco) return;
    
    // We register hover provider once for each language if needed.
    // However, monaco.editor.setModelMarkers already provides built-in hovers for markers.
    // We will rely on built-in marker tooltips for simplicity, as they are specifically designed for issues.
  }, []);

  // Sync Issues to Editor (Markers + Heatmap)
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (!editorRef.current) return;
      const monaco = window.monaco;
      if (!monaco) return;
      
      const model = editorRef.current.getModel();
      if (!model) return;

      if (!analysisResult || !analysisResult.issues) {
        monaco.editor.setModelMarkers(model, "ai", []);
        if (decorationsCollectionRef.current) {
          decorationsCollectionRef.current.clear();
        }
        return;
      }

      const issues = analysisResult.issues;
      const allIssues = [...issues, ...(analysisResult.ai_suggestions?.suggestions || [])];
      
      const MAX_MARKERS = 50;
      const visibleIssues = allIssues.slice(0, MAX_MARKERS);

      // Group by line to prevent overlap
      const grouped = {};
      visibleIssues.forEach(issue => {
        if (issue.scope === "global") return; // Skip global issues for markers
        const line = issue.line || 1;
        if (!grouped[line]) grouped[line] = [];
        grouped[line].push(issue);
      });

      const severityMap = {
        high: monaco.MarkerSeverity.Error,
        medium: monaco.MarkerSeverity.Warning,
        low: monaco.MarkerSeverity.Info
      };

      const heatmapColors = {
        high: "bg-rose-500/20",
        medium: "bg-amber-500/20",
        low: "bg-blue-500/10"
      };

      const markers = [];
      const decorations = [];

      Object.keys(grouped).forEach(lineStr => {
        const line = parseInt(lineStr, 10);
        const lineIssues = grouped[line];
        
        const highestSeverityIssue = lineIssues.reduce((prev, curr) => {
          return severityMap[curr.severity] > severityMap[prev.severity] ? curr : prev;
        }, lineIssues[0]);

        const mergedMessage = lineIssues.map(i => `[${(i.type || 'insight').toUpperCase()}] ${i.message || i.problem}`).join('\\n\\n');

        markers.push({
          startLineNumber: line,
          startColumn: 1,
          endLineNumber: line,
          endColumn: model.getLineMaxColumn(line) || 1000,
          message: mergedMessage,
          severity: severityMap[highestSeverityIssue.severity] || monaco.MarkerSeverity.Warning,
        });

        const colorClass = heatmapColors[highestSeverityIssue.severity] || heatmapColors.low;
        decorations.push({
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: colorClass
          }
        });
      });

      monaco.editor.setModelMarkers(model, "ai", markers);
      
      if (!decorationsCollectionRef.current) {
        decorationsCollectionRef.current = editorRef.current.createDecorationsCollection(decorations);
      } else {
        decorationsCollectionRef.current.set(decorations);
      }

    }, 200);

    return () => {
      clearTimeout(timeout);
      // We deliberately do NOT clear markers here to prevent blinking.
      // monaco.editor.setModelMarkers naturally overwrites old markers 
      // when it runs again, providing a smooth visual transition.
    };
  }, [analysisResult]);
  return (
    <div className="flex flex-col lg:flex-row h-screen bg-slate-950 text-slate-50 overflow-hidden">
      {/* Sidebar */}
      <div className="w-full lg:w-64 flex-shrink-0">
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative border-r border-slate-800">
        {/* Editor Toolbar */}
        <div className="h-14 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between px-4 z-10 glass-nav">
          <div className="flex items-center gap-4">
            <select 
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                // Trigger re-analysis cleanly on language change
                setTimeout(() => runAnalysis(code), 100);
              }}
              className="bg-slate-800 border border-slate-700 text-sm text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="python">Python</option>
              <option value="cpp">C++</option>
              <option value="java">Java</option>
            </select>
          </div>
          
          <div className="flex items-center gap-4">
            {isAnalyzing && <span className="text-xs text-slate-400 font-medium animate-pulse">Analyzing...</span>}
            <span className="hidden opacity-60 ml-2 text-xs md:inline">Ctrl+Enter to force</span>
          </div>
        </div>

        {/* Code Editor */}
        <div className="flex-1 relative">
          <Editor
            height="100%"
            language={language}
            theme="vs-dark"
            defaultValue={code}
            onChange={handleChange}
            onMount={handleEditorDidMount}
            beforeMount={handleEditorBeforeMount}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              fontFamily: "'JetBrains Mono', monospace",
              padding: { top: 16 },
              cursorBlinking: 'smooth',
              smoothScrolling: true,
              formatOnType: true,
              automaticLayout: true,
              scrollBeyondLastLine: false,
              wordWrap: 'on'
            }}
          />
        </div>
      </div>

      {/* Analysis Panel */}
      <div className="w-full lg:w-96 overflow-y-auto bg-slate-900 relative">
        <AnalysisPanel editorRef={editorRef} onRetry={() => runAnalysis(code)} />
      </div>

      {/* Floating Chatbox */}
      <Chatbox />
    </div>
  );
};

export default Dashboard;
