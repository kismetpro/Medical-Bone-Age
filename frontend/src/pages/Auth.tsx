import { useState, type FormEvent, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Activity, ShieldCheck, Stethoscope, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from '../config';
import { useAuth, type AuthRole } from '../context/AuthContext';
import styles from './Auth.module.css';

const loginRoles: Array<{ value: AuthRole; label: string; icon: ReactNode }> = [
  { value: 'user', label: '个人用户', icon: <User size={18} /> },
  { value: 'doctor', label: '临床医生', icon: <Stethoscope size={18} /> },
  { value: 'super_admin', label: '超级管理员', icon: <ShieldCheck size={18} /> },
];

const registerRoles: Array<{ value: 'user' | 'doctor'; label: string; icon: ReactNode }> = [
  { value: 'user', label: '个人用户', icon: <User size={18} /> },
  { value: 'doctor', label: '临床医生', icon: <Stethoscope size={18} /> },
];

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState<AuthRole>('user');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [doctorKey, setDoctorKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const roleOptions = isLogin ? loginRoles : registerRoles;

  const handleModeToggle = () => {
    setIsLogin((prev) => {
      const next = !prev;
      if (!next && role === 'super_admin') {
        setRole('user');
      }
      return next;
    });
    setDoctorKey('');
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    const payload: Record<string, string> = { username, password, role };
    if (!isLogin && role === 'doctor') {
      payload.admin_key = doctorKey;
    }

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || '认证失败');
      }

      login({
        username: data.username,
        role: data.role,
        token: data.token,
      });

      if (data.role === 'user') {
        navigate('/user-dashboard');
      } else {
        navigate('/doctor-dashboard');
      }
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : '认证过程中发生错误';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.authContainer}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.authCard}
      >
        <div className={styles.headerArea}>
          <Activity className={styles.iconPrimary} size={40} />
          <h2>骨龄智能平台</h2>
          <p>{isLogin ? '欢迎回来，请登录您的账号。' : '创建账号后即可开始使用系统。'}</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.formArea}>
          <div
            className={styles.roleSelector}
            style={{ gridTemplateColumns: `repeat(${roleOptions.length}, minmax(0, 1fr))` }}
          >
            {roleOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`${styles.roleBtn} ${role === option.value ? styles.active : ''}`}
                onClick={() => setRole(option.value)}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>

          <div className={styles.inputGroup}>
            <label>用户名</label>
            <input
              type="text"
              placeholder="至少 3 个字符"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>

          <div className={styles.inputGroup}>
            <label>密码</label>
            <input
              type="password"
              placeholder="至少 8 位，包含大小写字母和数字"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {!isLogin && role === 'doctor' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className={styles.inputGroup}
            >
              <label>医生注册密钥</label>
              <input
                type="password"
                placeholder="临床医生注册时必填"
                required
                value={doctorKey}
                onChange={(event) => setDoctorKey(event.target.value)}
              />
            </motion.div>
          )}

          {!isLogin && (
            <p style={{ margin: 0, fontSize: '0.83rem', color: '#64748b' }}>
              超级管理员账号不支持公开注册，只能由系统迁移或超级管理员后台创建。
            </p>
          )}

          {error && <div className={styles.errorMsg}>{error}</div>}

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? '处理中...' : isLogin ? '登录' : '注册'}
          </button>
        </form>

        <div className={styles.toggleArea}>
          <button onClick={handleModeToggle} type="button">
            {isLogin ? '没有账号？去注册' : '已有账号？去登录'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
