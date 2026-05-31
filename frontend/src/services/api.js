import axios from 'axios';
import toast from 'react-hot-toast';
import useStore from '../store/useStore';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const api = axios.create({
  baseURL: BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.defaults.withCredentials = true;

// Mock Backend Implementation Switch
const USE_MOCK = false;

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const analyzeCode = async (code, language, options = {}) => {
  if (USE_MOCK) {
    await delay(1500); // Simulate network latency
    
    // Simplistic mock logic based on language
    if (!code || code.trim() === '') {
      throw new Error("Code cannot be empty");
    }

    return {
      issues: [
        { line: 2, message: "Unused variable 'x'" },
        { line: 5, message: "Avoid nested loops for better performance" }
      ],
      complexity: "O(n²)",
      spaceComplexity: "O(n)",
      suggestions: [
        "Use a hash map or dictionary to reduce time complexity to O(n).",
        "Remove unused variables to clean up the code."
      ],
      optimizedCode: `// Optimized version\nfunction optimized() {\n  const map = new Map();\n  // logic here\n}`,
      score: 7.5
    };
  }

  try {
    const response = await api.post('/api/analyze', { code, language }, { timeout: 60000, ...options });
    const data = response.data;
    
    // Map Flask responses to the expected React structure
    return {
      issues: data.issues || [],
      complexity: data.time_complexity,
      spaceComplexity: data.space_complexity,
      ai_suggestions: data.ai_suggestions || {},
      score: data.summary ? Math.max(0, 10 - (
        (data.summary.high_issues || 0) * 2 + 
        (data.summary.medium_issues || 0) * 1 + 
        (data.summary.low_issues || 0) * 0.5
      )).toFixed(1) : 10,
    };
  } catch (error) {
    toast.error(error.response?.data?.error || error.response?.data?.message || 'Failed to analyze code');
    throw error;
  }
};

export const loginUser = async (email, password) => {
  if (USE_MOCK) {
    await delay(800);
    if (email === "test@example.com" && password === "password") {
      return { token: "mock-jwt-token", user: { id: 1, email } };
    }
    throw new Error("Invalid credentials - use test@example.com / password");
  }

  try {
    const response = await api.post('/api/login', { email, password });
    return response.data;
  } catch (error) {
    if (error.response?.status === 403 && error.response?.data?.requires_verification) {
      return error.response.data; // Return the verification requirement instead of throwing
    }
    toast.error(error.response?.data?.message || 'Login failed');
    throw error;
  }
};

export const signupUser = async (email, password) => {
  if (USE_MOCK) {
    await delay(800);
    return { requires_verification: true };
  }

  try {
    const response = await api.post('/api/signup', { email, password });
    return response.data;
  } catch (error) {
    toast.error(error.response?.data?.message || 'Signup failed');
    throw error;
  }
};

export const verifyEmail = async (email, otp) => {
  if (USE_MOCK) {
    await delay(1000);
    if (otp === "123456") return { token: "mock-jwt-token", user: { id: 2, email } };
    throw new Error("Invalid OTP");
  }

  try {
    const response = await api.post('/api/verify-email', { email, otp });
    return response.data;
  } catch (error) {
    toast.error(error.response?.data?.message || 'Verification failed');
    throw error;
  }
};

export const resendOtp = async (email) => {
  if (USE_MOCK) {
    await delay(1000);
    return { success: true };
  }

  try {
    const response = await api.post('/api/resend-otp', { email });
    toast.success(response.data.message || 'OTP resent successfully');
    return response.data;
  } catch (error) {
    toast.error(error.response?.data?.message || 'Failed to resend OTP');
    throw error;
  }
};

export const fetchUserHistory = async () => {
  if (USE_MOCK) {
    await delay(800);
    return [];
  }
  
  const state = useStore.getState();
  if (state.isGuest) {
    const guestHistory = sessionStorage.getItem('guest_history');
    return guestHistory ? JSON.parse(guestHistory) : [];
  }

  try {
    const response = await api.get('/api/history');
    return response.data.history || [];
  } catch (error) {
    toast.error(error.response?.data?.message || 'Failed to fetch history');
    return [];
  }
};

export const deleteHistoryItem = async (id) => {
  if (USE_MOCK) return true;
  
  const state = useStore.getState();
  if (state.isGuest) {
    return true; // Already handled by frontend state for guests
  }
  
  try {
    await api.delete(`/api/history/${id}`);
    return true;
  } catch (error) {
    toast.error(error.response?.data?.message || 'Failed to delete history item');
    return false;
  }
};

export const checkSession = async () => {
  try {
    const response = await api.get('/api/session');
    return response.data;
  } catch (error) {
    return null; /* Not logged in */
  }
};

// Chatbox Engine Endpoint
export const chatWithAI = async (payload, options = {}) => {
  try {
    const response = await api.post('/api/chat', payload, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    return response.data;
  } catch (error) {
    if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED' || error.message === 'canceled') {
      throw { isCanceled: true, message: 'Request aborted by user' };
    }
    throw new Error(error.response?.data?.error || error.response?.data?.message || 'Chat engine failed to connect');
  }
};
