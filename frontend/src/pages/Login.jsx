import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Terminal, Lock, Mail, Loader2, ArrowRight } from 'lucide-react';
import { loginUser } from '../services/api';
import useStore from '../store/useStore';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { setToken, setUser, setGuest } = useStore();

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await loginUser(email, password);
      
      if (response.requires_verification) {
        localStorage.setItem("pending_email", email);
        navigate('/verify-email');
        return;
      }
      
      // In a real app the user might be mapped properly
      setToken(response.token);
      setUser(response.user);
      navigate('/dashboard');
    } catch (error) {
      // Error is handled by toast in api.js
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex text-slate-50">
      {/* Left side Branding */}
      <div className="hidden lg:flex w-1/2 bg-slate-900 border-r border-white/10 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent pointer-events-none" />
        <Link to="/" className="flex items-center gap-2 font-bold text-2xl z-10 w-max">
          <Terminal className="text-indigo-500 w-8 h-8" />
          <span>CodeReview<span className="text-indigo-500">.ai</span></span>
        </Link>
        <div className="z-10 mt-auto">
          <h2 className="text-4xl font-bold mb-4 drop-shadow-sm leading-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">
            Welcome back to the future of coding.
          </h2>
          <p className="text-slate-400 text-lg">Sign in to access your analytics, history, and personalized review settings.</p>
        </div>
      </div>

      {/* Right side Form */}
      <div className="flex-1 bg-slate-950 flex items-center justify-center p-8 sm:p-12 relative">
        <div className="max-w-md w-full">
          <div className="mb-10 text-center lg:text-left">
            <h1 className="text-3xl font-bold mb-2">Sign in to your account</h1>
            <p className="text-slate-400">Enter your email and password below</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input 
                  type="email" 
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                  placeholder="m@example.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium text-slate-300">Password</label>
                <a href="#" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">Forgot password?</a>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Log in'}
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-400">
            Don't have an account?{' '}
            <Link to="/signup" className="text-indigo-400 hover:text-indigo-300 font-medium ml-1">
              Sign up
            </Link>
          </div>
          <div className="mt-4 text-center">
             <button onClick={() => { setGuest(true); navigate('/dashboard') }} className="text-slate-500 hover:text-slate-300 transition-colors text-sm flex items-center justify-center gap-1 mx-auto">
               Continue as guest <ArrowRight className="w-4 h-4" />
             </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
