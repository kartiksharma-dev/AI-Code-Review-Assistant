import { useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import useStore from '../store/useStore';
import { fetchUserHistory, deleteHistoryItem } from '../services/api';
import { Code2, Clock, Trash2, CalendarDays, Loader2 } from 'lucide-react';

const History = () => {
  const { history, setHistory, isLoadingHistory, setIsLoadingHistory, removeHistoryItem } = useStore();

  const handleDelete = async (id) => {
    // Optimistic UI update
    removeHistoryItem(id);
    // Background API call
    await deleteHistoryItem(id);
  };

  useEffect(() => {
    const loadData = async () => {
      setIsLoadingHistory(true);
      const data = await fetchUserHistory();
      setHistory(data);
      setIsLoadingHistory(false);
    };
    loadData();
  }, []);

  const getScoreColor = (sc) => {
    const numSc = parseFloat(sc);
    if (numSc >= 8) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    if (numSc >= 5) return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
    return 'text-red-400 bg-red-400/10 border-red-400/20';
  };

  const formatDate = (isoString) => {
    try {
      const d = new Date(isoString);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
    } catch {
      return isoString;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
        <h1 className="text-3xl font-bold mb-8">Analysis History</h1>

        {isLoadingHistory ? (
          <div className="flex flex-col items-center justify-center p-16 text-center h-[50vh]">
            <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
            <p className="text-slate-400">Loading your analysis history...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-center border border-dashed border-slate-700/50 rounded-2xl bg-slate-900/30">
            <Clock className="w-16 h-16 text-slate-600 mb-4" />
            <h3 className="text-xl font-medium text-slate-300">No History Yet</h3>
            <p className="text-slate-500 mt-2 max-w-sm">
              Your analysis results will appear here once you start using the code reviewer.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {history.map((item) => (
              <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-indigo-500/50 transition-all group flex flex-col">
                <div className="p-5 flex justify-between items-start border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-slate-500" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{item.language}</span>
                  </div>
                  <div className={`px-2 py-0.5 rounded-md text-xs font-bold border ${getScoreColor(item.score)}`}>
                    Score: {item.score}
                  </div>
                </div>
                
                <div className="p-4 flex-1">
                  <div className="bg-slate-950/50 rounded-lg border border-slate-800/80 p-3">
                    <pre className="text-xs font-mono text-slate-400 overflow-y-auto whitespace-pre-wrap max-h-72 custom-scrollbar">
                      {item.codeSnippet}
                    </pre>
                  </div>
                </div>
                
                <div className="p-4 bg-slate-950/50 border-t border-slate-800 flex justify-between items-center mt-auto">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <CalendarDays className="w-3.5 h-3.5" />
                    {formatDate(item.date)}
                  </div>
                  <button 
                    onClick={() => handleDelete(item.id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
