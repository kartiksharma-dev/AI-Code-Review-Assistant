import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Terminal, ShieldCheck, Loader2, ArrowRight, RefreshCw, XCircle, Mail } from 'lucide-react';
import toast from 'react-hot-toast';
import { verifyEmail, resendOtp } from '../services/api';
import useStore from '../store/useStore';

const VerifyEmail = () => {
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isError, setIsError] = useState(false);
  const [timer, setTimer] = useState(60);
  const [canResend, setCanResend] = useState(false);
  const inputRefs = useRef([]);
  const navigate = useNavigate();
  const { setToken, setUser } = useStore();

  useEffect(() => {
    const savedEmail = localStorage.getItem('pending_email');
    if (!savedEmail) {
      toast.error("No pending verification found. Please sign up again.");
      navigate('/signup');
    } else {
      setEmail(savedEmail);
    }
  }, [navigate]);

  useEffect(() => {
    let interval;
    if (timer > 0) {
      interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
    } else {
      setCanResend(true);
    }
    return () => clearInterval(interval);
  }, [timer]);

  const handleChange = (index, e) => {
    const value = e.target.value;
    if (isNaN(value)) return;

    const newOtp = [...otp];
    // allow only one digit
    newOtp[index] = value.substring(value.length - 1);
    setOtp(newOtp);

    // auto focus next
    if (value && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1].focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0 && inputRefs.current[index - 1]) {
      inputRefs.current[index - 1].focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text/plain').slice(0, 6).split('');
    if (pastedData.some(isNaN)) return;
    
    const newOtp = [...otp];
    pastedData.forEach((char, index) => {
      if (index < 6) newOtp[index] = char;
    });
    setOtp(newOtp);
    
    // Focus last filled input
    const nextIndex = Math.min(pastedData.length, 5);
    if (inputRefs.current[nextIndex]) {
      inputRefs.current[nextIndex].focus();
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    const otpValue = otp.join('');
    if (otpValue.length < 6) {
      toast.error('Please enter the full 6-digit code');
      return;
    }

    setIsLoading(true);
    setIsError(false);

    try {
      const { token, user } = await verifyEmail(email, otpValue);
      setIsSuccess(true);
      setToken(token);
      setUser(user);
      localStorage.removeItem('pending_email');
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
      
    } catch (error) {
      setIsError(true);
      // Reset after animation
      setTimeout(() => setIsError(false), 500);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (!canResend) return;
    setIsLoading(true);
    try {
      await resendOtp(email);
      setTimer(60);
      setCanResend(false);
    } catch (error) {
      // Error handled by toast in api.js
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden text-slate-50">
      <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 via-slate-950 to-indigo-500/5 pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full relative z-10"
      >
        <div className="bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-2xl p-8 sm:p-10 shadow-2xl relative overflow-hidden">
          
          {/* Neon Top Glow */}
          <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />

          <div className="flex justify-center mb-8">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center border border-white/5 relative">
              {isSuccess ? (
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute inset-0 bg-emerald-500 rounded-full flex items-center justify-center">
                  <ShieldCheck className="w-8 h-8 text-white" />
                </motion.div>
              ) : (
                <Mail className="w-8 h-8 text-emerald-400" />
              )}
            </div>
          </div>

          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold mb-2">Verify your email</h1>
            <p className="text-slate-400 text-sm">
              We've sent a secure 6-digit code to <br />
              <span className="font-semibold text-slate-200">{email}</span>
            </p>
          </div>

          <form onSubmit={handleVerify}>
            <motion.div 
              className="flex justify-center gap-2 sm:gap-3 mb-8"
              animate={isError ? { x: [-10, 10, -10, 10, 0] } : {}}
              transition={{ duration: 0.4 }}
            >
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => (inputRefs.current[index] = el)}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleChange(index, e)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  onPaste={handlePaste}
                  className="w-12 h-14 sm:w-14 sm:h-16 bg-slate-950/50 border border-slate-700 rounded-xl text-center text-xl sm:text-2xl font-bold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                />
              ))}
            </motion.div>

            <button
              type="submit"
              disabled={isLoading || isSuccess}
              className={`w-full font-semibold py-3 sm:py-4 rounded-xl transition-all flex items-center justify-center gap-2 mb-6
                ${isSuccess ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25' : 
                isError ? 'bg-red-500 text-white' : 
                'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/25 disabled:opacity-70'}
              `}
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 
               isSuccess ? 'Verified Successfully!' : 
               isError ? <><XCircle className="w-5 h-5" /> Verification Failed</> :
               <><ShieldCheck className="w-5 h-5" /> Verify Code</>
              }
            </button>
          </form>

          <div className="text-center">
            <p className="text-sm text-slate-400 flex items-center justify-center gap-2">
              Didn't receive the code?
              {canResend ? (
                <button 
                  type="button" 
                  onClick={handleResend}
                  className="text-emerald-400 font-medium hover:text-emerald-300 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Resend OTP
                </button>
              ) : (
                <span className="text-slate-500 font-medium">
                  Resend in <span className="text-emerald-500">{timer}s</span>
                </span>
              )}
            </p>
          </div>

        </div>
      </motion.div>
    </div>
  );
};

export default VerifyEmail;
