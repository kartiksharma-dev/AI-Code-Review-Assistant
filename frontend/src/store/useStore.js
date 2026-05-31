import { create } from 'zustand';

const useStore = create((set) => ({
  user: null,
  isGuest: false,
  isLoadingSession: true,
  token: localStorage.getItem('token') || null,
  code: '// Write your code here...\n',
  language: 'javascript',
  analysisResult: null,
  isAnalyzing: false,
  aiState: 'idle', // 'idle' | 'analyzing' | 'generating' | 'failed'
  aiError: null,
  lastAnalysisTime: null,
  history: [],
  isLoadingHistory: false,
  aiFixTimeline: [], // PHASE 4: Diff Engine & Change Tracking metadata
  
  // AI Chatbox State
  chatHistory: [],
  isChatOpen: false,
  isChatLoading: false,
  activeContext: null, // Track anchored issues

  setIsLoadingSession: (isLoadingSession) => set({ isLoadingSession }),
  setUser: (user) => set((state) => {
    state.resetWorkspace();
    return { user, isGuest: false, history: [] };
  }),
  setGuest: (isGuest) => set((state) => {
    if (isGuest) {
      sessionStorage.removeItem('guest_history');
      state.resetWorkspace();
    }
    return { isGuest, user: null };
  }),
  setToken: (token) => {
    localStorage.setItem('token', token);
    set({ token });
  },
  logout: () => set((state) => {
    localStorage.removeItem('token');
    sessionStorage.removeItem('guest_history');
    state.resetWorkspace();
    return { user: null, token: null, isGuest: false, history: [] };
  }),
  resetWorkspace: () => set({
    code: 'print("Hello World")\n',
    language: 'python',
    analysisResult: null,
    isAnalyzing: false,
    aiState: 'idle',
    aiError: null,
    lastAnalysisTime: null,
    aiFixTimeline: []
  }),
  setCode: (code) => set({ code }),
  setLanguage: (language) => set({ language }),
  setAnalysisResult: (analysisResult) => set({ analysisResult }),
  setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
  setAiState: (aiState) => set({ aiState }),
  setAiError: (aiError) => set({ aiError }),
  setLastAnalysisTime: (lastAnalysisTime) => set({ lastAnalysisTime }),
  addToHistory: (record) => set((state) => {
    const newHistory = [record, ...state.history];
    if (state.isGuest) {
      sessionStorage.setItem('guest_history', JSON.stringify(newHistory));
    }
    return { history: newHistory };
  }),
  setHistory: (history) => set({ history }),
  removeHistoryItem: (id) => set((state) => {
    const newHistory = state.history.filter(item => item.id !== id);
    if (state.isGuest) {
      sessionStorage.setItem('guest_history', JSON.stringify(newHistory));
    }
    return { history: newHistory };
  }),
  setIsLoadingHistory: (isLoadingHistory) => set({ isLoadingHistory }),
  addAIFixToTimeline: (fixRecord) => set((state) => ({ aiFixTimeline: [fixRecord, ...state.aiFixTimeline] })),
  removeLatestAIFixFromTimeline: () => set((state) => ({ aiFixTimeline: state.aiFixTimeline.slice(1) })),
  
  // Chatbox Actions
  setChatHistory: (chatHistory) => set({ chatHistory }),
  addChatMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
  clearChat: () => set({ chatHistory: [], activeContext: null }),
  setIsChatOpen: (isChatOpen) => set({ isChatOpen }),
  setIsChatLoading: (isChatLoading) => set({ isChatLoading }),
  setActiveContext: (activeContext) => set({ activeContext }),
}));

export default useStore;
