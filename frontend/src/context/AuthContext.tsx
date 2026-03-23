import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { AuthCookie } from '../lib/cookieManager';

export type AuthRole = 'user' | 'doctor' | 'super_admin';
type Role = AuthRole | null;

interface StoredUser {
  username: string;
  role: string;
  token?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  role: Role;
  username: string | null;
  login: (userData: StoredUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  role: null,
  username: null,
  login: () => { },
  logout: () => { },
});

const normalizeRole = (value: unknown): Role => {
  if (value === 'admin') return 'doctor';
  if (value === 'user' || value === 'doctor' || value === 'super_admin') return value;
  return null;
};

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState<Role>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('boneage_user');
    const cookieUser = AuthCookie.getUser();
    const user = storedUser ? JSON.parse(storedUser) : cookieUser;
    
    if (!user) return;

    try {
      const normalizedRole = normalizeRole(user.role);
      if (!normalizedRole || !user.username) {
        throw new Error('Invalid stored session');
      }

      setIsAuthenticated(true);
      setRole(normalizedRole);
      setUsername(user.username);
      
      const normalizedUser = { ...user, role: normalizedRole };
      localStorage.setItem('boneage_user', JSON.stringify(normalizedUser));
      AuthCookie.setUser(normalizedUser);

      if (user.token) {
        localStorage.setItem('boneage_token', user.token);
        AuthCookie.setToken(user.token);
      }
    } catch (error) {
      console.error('Failed to parse user session', error);
      localStorage.removeItem('boneage_user');
      localStorage.removeItem('boneage_token');
      AuthCookie.clearAuth();
    }
  }, []);

  const login = (userData: StoredUser) => {
    const normalizedRole = normalizeRole(userData.role);
    if (!normalizedRole) {
      throw new Error('不支持的用户角色');
    }

    const normalizedUser = { ...userData, role: normalizedRole };
    setIsAuthenticated(true);
    setRole(normalizedRole);
    setUsername(userData.username);
    
    localStorage.setItem('boneage_user', JSON.stringify(normalizedUser));
    AuthCookie.setUser(normalizedUser);

    if (userData.token) {
      localStorage.setItem('boneage_token', userData.token);
      AuthCookie.setToken(userData.token);
    } else {
      localStorage.removeItem('boneage_token');
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setRole(null);
    setUsername(null);
    
    localStorage.removeItem('boneage_user');
    localStorage.removeItem('boneage_token');
    localStorage.removeItem('boneage_history');
    
    AuthCookie.clearAuth();
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
