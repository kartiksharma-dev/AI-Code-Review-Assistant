import { Link, useNavigate } from 'react-router-dom';
import useStore from '../store/useStore';
import { Terminal, Shield, Zap, Sparkles, ChevronRight, Github } from 'lucide-react';

const Landing = () => {
  const { setGuest } = useStore();
  const navigate = useNavigate();

  const handleStartFree = () => {
    setGuest(true);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-50 selection:bg-indigo-500/30">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-6 py-4 md:px-12 lg:px-24 border-b border-white/10 glass-nav z-50">
        <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
          <Terminal className="text-indigo-500 w-6 h-6" />
          <span>CodeReview<span className="text-indigo-500">.ai</span></span>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium">
          <Link to="/login" className="text-slate-300 hover:text-white transition-colors">Log in</Link>
          <Link to="/signup" className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-full transition-all shadow-lg hover:shadow-indigo-500/25">
            Sign up
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 pt-20 pb-32">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-sm font-medium mb-8 border border-indigo-500/20">
          <Sparkles className="w-4 h-4" />
          <span>Powered by Advanced AI Models</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl text-transparent bg-clip-text bg-gradient-to-br from-white to-slate-400 mb-6 drop-shadow-sm">
          Ship better code, <br className="hidden md:block"/> faster than ever.
        </h1>
        
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mb-10 leading-relaxed">
          Your personal AI Code Review Assistant. Instantly analyze your logic, identify bugs, understand complexity, and get optimized suggestions directly in the browser.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full justify-center max-w-md">
          <button 
            onClick={handleStartFree}
            className="w-full sm:w-auto px-8 py-3 rounded-xl bg-white text-slate-900 font-semibold hover:bg-slate-200 transition-all flex items-center justify-center gap-2 group"
          >
            Start Free
            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          <Link 
            to="/signup"
            className="w-full sm:w-auto px-8 py-3 rounded-xl bg-slate-800 text-white font-semibold hover:bg-slate-700 transition-all border border-slate-700 flex items-center justify-center gap-2"
          >
            <Github className="w-4 h-4" />
            Sign in with GitHub
          </Link>
        </div>
      </main>

      {/* Features Showcase */}
      <section className="bg-slate-950/50 py-24 px-6 md:px-12 lg:px-24 border-t border-white/5">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              icon: <Zap className="text-amber-400 w-8 h-8" />,
              title: "Instant Analysis",
              desc: "Get real-time feedback on your code syntax, possible memory leaks, and runtime errors before they hit production."
            },
            {
              icon: <Shield className="text-emerald-400 w-8 h-8" />,
              title: "Security Hardening",
              desc: "Identify potential security vulnerabilities and get best-practice implementations with an explanation of why it matters."
            },
            {
              icon: <Terminal className="text-indigo-400 w-8 h-8" />,
              title: "Complexity Metrics",
              desc: "Visualize your Big O Time and Space complexity. AI suggests refactors to optimize those expensive nested loops."
            }
          ].map((feat, i) => (
            <div key={i} className="p-8 rounded-3xl bg-slate-900/50 border border-white/5 hover:border-indigo-500/30 transition-colors group">
              <div className="bg-slate-800/50 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                {feat.icon}
              </div>
              <h3 className="text-xl font-bold mb-3">{feat.title}</h3>
              <p className="text-slate-400 leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-slate-500 text-sm border-t border-white/5">
        <p>&copy; {new Date().getFullYear()} CodeReview.ai Labs. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default Landing;
