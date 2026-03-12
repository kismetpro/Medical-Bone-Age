import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

type Role = 'user' | 'admin' | null;

interface AuthContextType {
  isAuthenticated: boolean;
  role: Role;
  username: string | null;
  login: (userData: { username: string; role: string; token?: string }) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  role: null,
  username: null,
  login: () => { },
  logout: () => { },
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [role, setRole] = useState<Role>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    // Check local storage for existing session on mount
    const storedUser = localStorage.getItem('boneage_user');
    if (storedUser) {
      try {
        const user = JSON.parse(storedUser);
        setIsAuthenticated(true);
        setRole(user.role);
        setUsername(user.username);
      } catch (e) {
        console.error('Failed to parse user session', e);
        localStorage.removeItem('boneage_user');
      }
    }
  }, []);

  const login = (userData: { username: string; role: string; token?: string }) => {
    setIsAuthenticated(true);
    setRole(userData.role as Role);
    setUsername(userData.username);
    localStorage.setItem('boneage_user', JSON.stringify(userData));
    if (userData.token) {
      localStorage.setItem('boneage_token', userData.token); // Store token if provided
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
    localStorage.removeItem('boneage_history'); // Optional: clear recent local history on logout
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
