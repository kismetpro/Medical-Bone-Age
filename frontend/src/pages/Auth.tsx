import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { Activity, ShieldCheck, User } from 'lucide-react';
import styles from './Auth.module.css';

import { API_BASE } from '../config';


export default function Auth() {
    const [isLogin, setIsLogin] = useState(true);
    const [role, setRole] = useState<'user' | 'admin'>('user');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [adminKey, setAdminKey] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        const endpoint = isLogin ? '/auth/login' : '/auth/register';
        const payload: any = { username, password, role };

        if (!isLogin && role === 'admin') {
            payload.admin_key = adminKey;
        }

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '认证失败');
            }

            login({
                username: data.username,
                role: data.role,
                token: data.token
            });

            if (data.role === 'admin') {
                navigate('/doctor-dashboard');
            } else {
                navigate('/user-dashboard');
            }

        } catch (err: any) {
            setError(err.message || '认证过程中发生错误。');
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
                    <p>{isLogin ? '欢迎回来，请登录。' : '创建您的账户以开始使用。'}</p>
                </div>

                <form onSubmit={handleSubmit} className={styles.formArea}>

                    <div className={styles.roleSelector}>
                        <button
                            type="button"
                            className={`${styles.roleBtn} ${role === 'user' ? styles.active : ''}`}
                            onClick={() => setRole('user')}
                        >
                            <User size={18} /> 个人用户
                        </button>
                        <button
                            type="button"
                            className={`${styles.roleBtn} ${role === 'admin' ? styles.active : ''}`}
                            onClick={() => setRole('admin')}
                        >
                            <ShieldCheck size={18} /> 临床医生
                        </button>
                    </div>

                    <div className={styles.inputGroup}>
                        <label>用户名</label>
                        <input
                            type="text"
                            placeholder="至少 3 个字符"
                            required
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                        />
                    </div>

                    <div className={styles.inputGroup}>
                        <label>密码</label>
                        <input
                            type="password"
                            placeholder="至少 8 位包含字母和数字"
                            required
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />
                    </div>

                    {!isLogin && role === 'admin' && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            className={styles.inputGroup}
                        >
                            <label>医生注册凭证</label>
                            <input
                                type="password"
                                placeholder="医生账号必填项"
                                required
                                value={adminKey}
                                onChange={e => setAdminKey(e.target.value)}
                            />
                        </motion.div>
                    )}

                    {error && <div className={styles.errorMsg}>{error}</div>}

                    <button type="submit" className={styles.submitBtn} disabled={loading}>
                        {loading ? '处理中...' : (isLogin ? '登录' : '注册')}
                    </button>
                </form>

                <div className={styles.toggleArea}>
                    <button onClick={() => { setIsLogin(!isLogin); setError(null); }} type="button">
                        {isLogin ? "没有账户？去注册" : "已有账户？去登录"}
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
