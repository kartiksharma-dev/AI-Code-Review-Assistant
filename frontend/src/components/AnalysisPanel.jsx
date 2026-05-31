import { useState, useMemo } from 'react';
import useStore from '../store/useStore';
import { AlertCircle, Zap, Code2, ShieldAlert, CheckCircle2, Copy, Check, ChevronDown, ChevronRight, Wand2, Info, ArrowRight, Activity, X, RotateCcw, Clock, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell } from 'recharts';
import { DiffEditor } from '@monaco-editor/react';

const complexityMap = {
  "O(1)": 1,
  "O(log n)": 3,
  "O(n)": 5,
  "O(n log n)": 7,
  "O(n²)": 10,
  "O(2^n)": 15
};

const getComplexityValue = (compStr) => {
  if (!compStr) return 1;
  const match = Object.keys(complexityMap).find(k => compStr.includes(k));
  return match ? complexityMap[match] : 5;
};

const SuggestionBlock = ({ sug, handlePreviewFix }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const typeColors = {
    performance: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    security: "bg-rose-500/20 text-rose-400 border-rose-500/30",
    readability: "bg-sky-500/20 text-sky-400 border-sky-500/30",
    best_practice: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
  };

  return (
    <div className="rounded-xl bg-slate-800/50 border border-slate-700 overflow-hidden hover:border-slate-600 transition-colors">
      <div 
        className="p-4 flex flex-col gap-3 cursor-pointer"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-start gap-3">
          {open ? <ChevronDown className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" /> : <ChevronRight className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${typeColors[sug.type] || typeColors.best_practice} uppercase tracking-wide`}>
                {sug.type.replace('_', ' ')}
              </span>
              {sug.source === 'ai' && (
                <span className="flex items-center gap-1 text-[10px] bg-purple-600/20 text-purple-400 px-2 py-0.5 rounded border border-purple-500/30">
                  <Wand2 className="w-3 h-3" /> AI
                </span>
              )}
            </div>
            <h4 className="text-slate-200 font-medium text-sm">
              {sug.problem}
            </h4>
          </div>
        </div>
      </div>

      {open && (
        <div className="px-4 pb-4 border-t border-slate-800/50 pt-3 bg-slate-800/20">
          {sug.drift_info?.has_drift && (
             <div className="mb-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                <div>
                   <h4 className="text-[11px] font-bold text-amber-500 uppercase tracking-wider mb-1">Potential Behavioral Change Detected</h4>
                   <p className="text-sm text-amber-200/80">{sug.drift_info.reason}</p>
                </div>
             </div>
          )}
          <p className="text-slate-300 text-sm mb-4 leading-relaxed">{sug.solution}</p>
          
          {/* Action Buttons */}
          <div className="flex items-center gap-3 mb-4">
            <button 
              onClick={(e) => { 
                e.stopPropagation(); 
                useStore.getState().setActiveContext(sug);
                useStore.getState().setIsChatOpen(true);
              }}
              className="flex items-center gap-1.5 text-xs font-medium text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg border border-indigo-500/20 transition-colors"
            >
              <Info className="w-3.5 h-3.5" /> Explain More
            </button>
            {sug.fixable && sug.example ? (
              <button 
                onClick={(e) => { e.stopPropagation(); handlePreviewFix(sug); }}
                className="flex items-center gap-1.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg shadow-lg shadow-indigo-500/20 transition-colors"
              >
                <Wand2 className="w-3.5 h-3.5" /> Preview Fix
              </button>
            ) : sug.example ? (
              <button 
                onClick={(e) => { e.stopPropagation(); alert('Optimize: Modal diff view coming soon!'); }}
                className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 px-3 py-1.5 rounded-lg border border-emerald-500/20 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" /> Optimize
              </button>
            ) : null}
          </div>

          {sug.example && sug.example.trim() !== "" && (
            <div className="border border-slate-800 bg-slate-950 rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-900/80">
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">Suggested Code</span>
                <button onClick={(e) => {
                  e.stopPropagation();
                  navigator.clipboard.writeText(sug.example);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }} className="text-slate-500 hover:text-white transition-colors">
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="p-3 text-xs text-slate-300 font-mono overflow-x-auto">
                <code className="break-words whitespace-pre-wrap">{sug.example}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const AnalysisPanel = ({ editorRef, onRetry }) => {
  const { analysisResult, isAnalyzing, code, setCode, language, addAIFixToTimeline, aiFixTimeline, removeLatestAIFixFromTimeline, aiState, aiError, setAiError, lastAnalysisTime, setActiveContext, setIsChatOpen } = useStore();
  const [activeTab, setActiveTab] = useState('issues');
  const [previewFix, setPreviewFix] = useState(null);

  const { issues = [], complexity, spaceComplexity, score, ai_suggestions = {} } = analysisResult || {};
  const suggestions = ai_suggestions?.suggestions || [];
  const explanation = ai_suggestions?.explanation || "";

  const isAiPowered = suggestions.some(s => s.source === 'ai');

  const confidenceScore = useMemo(() => {
    if (!suggestions.length) return null;
    return Math.min(95, 60 + (suggestions.length * 5) + (explanation ? 10 : 0));
  }, [suggestions.length, explanation]);

  const severityColors = {
    high: "bg-rose-500/20 text-rose-400 border-rose-500/30",
    medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    low: "bg-sky-500/20 text-sky-400 border-sky-500/30"
  };

  const severityOrder = { high: 3, medium: 2, low: 1 };

  const groupedIssues = useMemo(() => {
    const groups = {};
    issues.forEach(issue => {
      const cat = issue.type || "best_practice";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(issue);
    });
    
    Object.keys(groups).forEach(cat => {
      groups[cat].sort((a, b) => (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0));
    });
    return groups;
  }, [issues]);

  const chartData = useMemo(() => {
    return [
      { name: "Time", value: getComplexityValue(complexity) },
      { name: "Space", value: getComplexityValue(spaceComplexity) }
    ];
  }, [complexity, spaceComplexity]);

  const handleIssueClick = (issue) => {
    if (issue.line && editorRef?.current) {
      editorRef.current.revealLineInCenter(issue.line);
      editorRef.current.setPosition({ lineNumber: issue.line, column: 1 });
      editorRef.current.focus();
    }
    setActiveContext(issue);
    setIsChatOpen(true);
  };

  const handlePreviewFix = (sug) => {
    if (!sug.example || sug.example.trim() === "") {
      alert("Validation Error: AI did not return valid replacement code.");
      return;
    }
    if (sug.example.trim() === code.trim()) {
      alert("Validation Error: The optimized code is identical to your original code. No fix needed.");
      return;
    }
    setPreviewFix(sug);
  };

  const applyFix = (sug) => {
    if (!editorRef?.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;

    const currentPosition = editorRef.current.getPosition();

    // Use pushEditOperations to preserve undo stack
    editorRef.current.executeEdits("ai-fix", [{
      range: model.getFullModelRange(),
      text: sug.example,
      forceMoveMarkers: true
    }]);

    if (currentPosition) {
       editorRef.current.setPosition(currentPosition);
    }

    // PHASE 4: Diff Engine & Change Tracking Metadata
    const originalLines = code.split('\n');
    const newLines = sug.example.split('\n');
    
    const fixRecord = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      problem: sug.problem,
      solution: sug.solution,
      type: sug.type,
      severity: sug.severity,
      originalCode: code,
      optimizedCode: sug.example,
      metadata: {
        linesChanged: Math.abs(newLines.length - originalLines.length),
        insertedLogic: newLines.length > originalLines.length,
        removedLogic: originalLines.length > newLines.length
      }
    };
    
    addAIFixToTimeline(fixRecord);

    // Update Zustand state so it stays synced
    setCode(sug.example);
    setPreviewFix(null);
  };

  const revertLastFix = () => {
    if (!aiFixTimeline || aiFixTimeline.length === 0) return;
    const lastFix = aiFixTimeline[0];
    
    if (!editorRef?.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;

    const currentPosition = editorRef.current.getPosition();

    // Restore original code transactionally
    editorRef.current.executeEdits("ai-revert", [{
      range: model.getFullModelRange(),
      text: lastFix.originalCode,
      forceMoveMarkers: true
    }]);

    if (currentPosition) {
       editorRef.current.setPosition(currentPosition);
    }

    setCode(lastFix.originalCode);
    removeLatestAIFixFromTimeline();
  };

  const renderErrorBanner = () => {
    if (aiState !== 'failed' || !aiError) return null;

    const colors = {
      danger: "bg-rose-500/10 border-rose-500/30 text-rose-300",
      warning: "bg-amber-500/10 border-amber-500/30 text-amber-300",
      info: "bg-sky-500/10 border-sky-500/30 text-sky-300",
      protected: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
    };

    const colorClass = colors[aiError.severity] || colors.danger;

    return (
      <div className={`m-4 p-4 rounded-xl border flex flex-col gap-3 ${colorClass} animate-[fade-in_0.3s_ease-out]`}>
        <div className="flex items-start justify-between">
           <div className="flex items-center gap-2.5">
             <AlertCircle className="w-4 h-4 shrink-0" />
             <span className="text-xs font-bold uppercase tracking-wider">{aiError.code.replace('_', ' ')}</span>
           </div>
           <button onClick={() => setAiError(null)} className="opacity-60 hover:opacity-100 transition-opacity">
             <X className="w-4 h-4" />
           </button>
        </div>
        <p className="text-sm opacity-90 leading-relaxed">{aiError.message}</p>
        
        {aiError.recoverable && (
          <button 
             onClick={() => { setAiError(null); if (onRetry) onRetry(); }}
             className="mt-1 self-start flex items-center gap-1.5 text-xs font-bold bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg transition-colors border border-white/10"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Request
          </button>
        )}
      </div>
    );
  };

  if (!analysisResult && !isAnalyzing && aiState !== 'failed') {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500 w-full bg-slate-900 relative overflow-hidden">
        <ShieldAlert className="w-16 h-16 mb-4 opacity-20" />
        <h3 className="text-lg font-medium text-slate-300">No Review Yet</h3>
        <p className="text-sm mt-2">Write some code to see live results.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'issues', label: 'Issues', count: issues.length },
    { id: 'suggestions', label: 'AI Intelligence', count: suggestions.length },
    { id: 'complexity', label: 'Metrics' }
  ];

  return (
    <div className="h-full flex flex-col w-full bg-slate-900 relative">
      {/* Small top progress bar instead of full-screen overlay */}
      {isAnalyzing && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-slate-800 z-50 overflow-hidden">
          <div className="h-full bg-indigo-500 w-full animate-pulse" />
        </div>
      )}

      {/* AI Identity Header */}
      <div className="p-5 border-b border-slate-800 bg-slate-900/50 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isAiPowered ? (
              <span className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-purple-600 text-white shadow-lg shadow-purple-500/20 border border-purple-500">
                <Wand2 className="w-3.5 h-3.5" /> AI Powered
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                <Activity className="w-3.5 h-3.5" /> Basic Analysis
              </span>
            )}
            <span className="text-xs text-slate-500">
              {isAiPowered ? 'Generated by Gemini AI' : 'Rule-based fallback'}
            </span>
          </div>
          {confidenceScore !== null && (
            <div className="flex items-center gap-3">
               {lastAnalysisTime && !isAnalyzing && aiState !== 'failed' && (
                  <div className="flex items-center gap-1 text-[10px] text-slate-500 font-medium bg-slate-800/50 px-2 py-0.5 rounded border border-slate-700">
                     <Clock className="w-3 h-3" />
                     {new Date(lastAnalysisTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                  </div>
               )}
               {aiFixTimeline?.length > 0 && (
                  <button onClick={revertLastFix} className="flex items-center gap-1.5 text-[10px] bg-rose-500/10 text-rose-400 px-2 py-1 rounded border border-rose-500/20 hover:bg-rose-500/20 hover:border-rose-500/40 transition-colors uppercase tracking-wider font-bold">
                     <RotateCcw className="w-3 h-3" /> Revert AI Fix
                  </button>
               )}
              {isAnalyzing && (
                <span className="text-[10px] text-indigo-400 uppercase tracking-wider font-semibold animate-pulse">
                  {code.length > 500 ? "Generating Optimization..." : "Analyzing..."}
                </span>
              )}
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Confidence:</span>
                <span className={`text-xs font-bold ${confidenceScore > 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {confidenceScore}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Render AI Error Banner if failed */}
      {renderErrorBanner()}

      {/* Tabs */}
      <div className="flex px-4 border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors relative ${
              activeTab === tab.id 
                ? 'border-indigo-500 text-indigo-400' 
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-2 bg-slate-800 text-slate-300 py-0.5 px-2 rounded-full text-[10px]">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {activeTab === 'issues' && (
          <div className="space-y-6">
            {issues.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                <CheckCircle2 className="w-10 h-10 text-emerald-500 mb-3" />
                <p className="text-emerald-400 font-medium text-sm">No issues found. Code looks clean.</p>
              </div>
            ) : (
              Object.entries(groupedIssues).map(([category, catIssues]) => (
                <div key={category} className="space-y-3">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    {category.replace('_', ' ')}
                    <span className="bg-slate-800 text-slate-500 text-[10px] px-2 py-0.5 rounded-full">{catIssues.length}</span>
                  </h3>
                  {catIssues.map((issue) => (
                    <div 
                      key={issue.id} 
                      onClick={() => handleIssueClick(issue)}
                      className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-slate-500 hover:bg-slate-800 transition-all cursor-pointer group"
                    >
                      <div className="flex items-start gap-3">
                        <AlertCircle className={`w-4 h-4 shrink-0 mt-0.5 ${
                          issue.severity === 'high' ? 'text-rose-500' : 
                          issue.severity === 'medium' ? 'text-amber-500' : 'text-sky-500'
                        }`} />
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-mono text-slate-400 group-hover:text-indigo-400 transition-colors">
                              {issue.scope === 'global' ? 'File Scope' : `Line ${issue.line}`}
                            </span>
                            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${severityColors[issue.severity] || severityColors.low}`}>
                              {issue.severity}
                            </span>
                          </div>
                          <p className="text-sm text-slate-200 mt-1">{issue.message}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'suggestions' && (
          <div className="space-y-5">
            {!isAnalyzing && explanation && explanation.trim() !== "" && (
              <div className="bg-blue-900/20 border border-blue-500/30 p-4 rounded-xl mb-2">
                <h3 className="text-blue-400 text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Wand2 className="w-3.5 h-3.5" /> AI Summary
                </h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {explanation}
                </p>
              </div>
            )}
            
            {suggestions.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-800/30 rounded-xl border border-slate-700/50">
                <CheckCircle2 className="w-10 h-10 text-slate-500 mb-3 opacity-50" />
                <p className="text-slate-300 font-medium text-sm">Analysis Complete</p>
                <p className="text-slate-500 text-xs mt-2 max-w-[250px]">
                  Your code is well-structured. No additional improvements found.
                </p>
              </div>
            ) : (
              suggestions.map((sug) => <SuggestionBlock key={sug.id} sug={sug} handlePreviewFix={handlePreviewFix} />)
            )}
          </div>
        )}

        {activeTab === 'complexity' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700 text-center">
                <div className="mx-auto w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center mb-2">
                  <Zap className="w-4 h-4 text-indigo-400" />
                </div>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Time</p>
                <p className="text-lg font-mono font-bold text-indigo-400 mt-1">{complexity || 'O(1)'}</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700 text-center">
                <div className="mx-auto w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center mb-2">
                  <Code2 className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Space</p>
                <p className="text-lg font-mono font-bold text-emerald-400 mt-1">{spaceComplexity || 'O(1)'}</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6 text-center">Complexity Analysis</h4>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                    <RechartsTooltip 
                      cursor={{ fill: '#1e293b', opacity: 0.4 }}
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#818cf8' : '#34d399'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AI Preview Modal */}
      {previewFix && (
        <div className="fixed inset-0 z-[100] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-5xl h-[80vh] flex flex-col overflow-hidden animate-[fade-in_0.2s_ease-out]">
            
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex flex-col gap-4 bg-slate-900/80">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    <Wand2 className="w-5 h-5 text-purple-400" />
                    AI Optimization Preview
                  </h2>
                  <p className="text-sm font-medium text-slate-300 mt-2">{previewFix.problem}</p>
                </div>
                <button onClick={() => setPreviewFix(null)} className="text-slate-400 hover:text-white transition-colors bg-slate-800/50 hover:bg-slate-700 p-2 rounded-lg shrink-0">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5 bg-slate-800/50 px-2.5 py-1.5 rounded border border-slate-700">
                  <span className="text-slate-400 font-medium">Risk Level:</span>
                  <span className={`font-bold ${previewFix.severity === 'high' ? 'text-rose-400' : previewFix.severity === 'medium' ? 'text-amber-400' : 'text-emerald-400'} uppercase tracking-wide`}>
                    {previewFix.severity || 'low'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 bg-slate-800/50 px-2.5 py-1.5 rounded border border-slate-700">
                  <span className="text-slate-400 font-medium">Confidence:</span>
                  <span className="font-bold text-emerald-400 tracking-wide">94%</span>
                </div>
              </div>

              {previewFix.diff_explanation ? (
                <div className="flex flex-col gap-3">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                     <div className="lg:col-span-2 bg-indigo-500/10 border border-indigo-500/20 p-4 rounded-xl flex flex-col justify-center">
                       <div className="flex items-center gap-2 mb-2">
                         <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider bg-indigo-500/20 border border-indigo-500/30 px-2 py-0.5 rounded">
                           {previewFix.diff_explanation.change_type?.replace('_', ' ') || 'Optimization'}
                         </span>
                       </div>
                       <p className="text-sm text-indigo-100 leading-relaxed font-medium mb-1.5">
                         {previewFix.diff_explanation.summary}
                       </p>
                       <p className="text-xs text-indigo-200/70">
                         {previewFix.diff_explanation.impact}
                       </p>
                     </div>
                     <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl flex flex-col justify-center">
                       <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                         <Activity className="w-3.5 h-3.5" /> Complexity Impact
                       </h4>
                       <div className="space-y-2 text-xs">
                          <div className="flex items-center justify-between border-b border-slate-700/50 pb-2">
                            <span className="text-slate-400 font-medium">Time</span>
                            <div className="flex items-center gap-2 font-mono">
                               <span className="text-slate-500 line-through">{previewFix.diff_explanation.complexity_before}</span>
                               <ArrowRight className="w-3 h-3 text-slate-500" />
                               <span className="text-emerald-400 font-bold">{previewFix.diff_explanation.complexity_after}</span>
                            </div>
                          </div>
                       </div>
                     </div>
                  </div>
                  {previewFix.diff_explanation.reasoning?.length > 0 && (
                    <div className="bg-slate-800/30 border border-slate-700 p-3 rounded-lg">
                       <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                         <Info className="w-3.5 h-3.5" /> Logical Adjustments
                       </h4>
                       <ul className="space-y-1.5 text-xs text-slate-300">
                         {previewFix.diff_explanation.reasoning.map((r, i) => (
                           <li key={i} className="flex items-start gap-2">
                             <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                             <span className="leading-relaxed">{r}</span>
                           </li>
                         ))}
                       </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-indigo-500/10 border border-indigo-500/20 p-3 rounded-lg">
                  <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider mb-1.5">Proposed Solution</h4>
                  <p className="text-sm text-indigo-200/90 leading-relaxed">{previewFix.solution}</p>
                </div>
              )}
            </div>

            {/* Monaco Diff Editor */}
            <div className="flex-1 bg-[#1e1e1e] relative">
              <DiffEditor
                original={code}
                modified={previewFix.example}
                language={language}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  renderSideBySide: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: "'JetBrains Mono', monospace",
                  scrollBeyondLastLine: false,
                }}
              />
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
              <button 
                 onClick={() => { 
                   setActiveContext(previewFix);
                   setIsChatOpen(true);
                   setPreviewFix(null);
                 }}
                 className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors border border-slate-700"
              >
                 <Info className="w-4 h-4 text-indigo-400" /> Explain More
              </button>
              
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setPreviewFix(null)}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => applyFix(previewFix)}
                  className="px-6 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2"
                >
                  <Check className="w-4 h-4" /> Apply Fix
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;
