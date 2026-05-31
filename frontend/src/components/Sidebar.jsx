import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Activity, History, Settings, LogOut, Terminal } from 'lucide-react';
import useStore from '../store/useStore';
import { useNavigate } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, isGuest, user } = useStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { name: 'History', path: '/history', icon: <History className="w-5 h-5" /> },
  ];

  return (
    <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-full">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 font-bold text-xl mb-8">
          <Terminal className="text-indigo-500 w-6 h-6" />
          <span className="text-slate-100">CodeReview<span className="text-indigo-500">.ai</span></span>
        </Link>

        {isGuest && (
          <div className="bg-slate-800/50 rounded-xl p-4 mb-6 border border-slate-700">
            <p className="text-xs text-amber-400 font-medium mb-1">Guest Mode</p>
            <p className="text-sm text-slate-400 mb-3">Your history won't be saved.</p>
            <Link to="/signup" className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition-colors block text-center">
              Create Account
            </Link>
          </div>
        )}

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link 
                key={item.name}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${
                  isActive 
                    ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' 
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                {item.icon}
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="mt-auto p-6 space-y-1">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition-all font-medium">
          <Settings className="w-5 h-5" />
          Settings
        </button>
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-400 hover:bg-red-500/10 transition-all font-medium"
        >
          <LogOut className="w-5 h-5" />
          {isGuest ? 'Exit Guest Mode' : 'Log out'}
        </button>
        
        {!isGuest && user && (
          <div className="pt-4 mt-2 border-t border-slate-800 flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white font-bold text-sm">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex flex-col truncate">
              <span className="text-sm font-medium text-slate-200 truncate">{user.email}</span>
              <span className="text-xs text-slate-500">Pro Plan</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
