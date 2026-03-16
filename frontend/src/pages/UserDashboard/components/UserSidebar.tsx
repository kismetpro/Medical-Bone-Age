import React from 'react';
import { Activity, History, MessageSquare, Bot, LogOut, User as UserIcon, Home } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import styles from '../UserDashboard.module.css';

interface UserSidebarProps {
    activeTab?: 'predict' | 'history' | 'community';
    setActiveTab?: (tab: 'predict' | 'history' | 'community') => void;
    username: string | null;
    handleLogout: () => void;
}

const UserSidebar: React.FC<UserSidebarProps> = ({ activeTab, setActiveTab, username, handleLogout }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const isDashboard = location.pathname === '/user-dashboard';
    const isConsultation = location.pathname === '/consultation';
    const isCommunity = location.pathname === '/community';

    return (
        <aside className={styles.sidebar}>
            <div className={styles.brand} style={{ cursor: 'pointer' }} onClick={() => navigate('/user-dashboard')}>
                <Activity size={24} color="#3b82f6" />
                <span>患者控制台</span>
            </div>

            <nav className={styles.sideNav}>
                <button 
                    className={`${styles.navItem} ${isDashboard && activeTab === 'predict' ? styles.active : ''}`} 
                    onClick={() => {
                        if (isDashboard && setActiveTab) setActiveTab('predict');
                        else navigate('/user-dashboard');
                    }}
                >
                    <Activity size={18} /> 预测评估
                </button>
                <button 
                    className={`${styles.navItem} ${isDashboard && activeTab === 'history' ? styles.active : ''}`} 
                    onClick={() => {
                        if (isDashboard && setActiveTab) setActiveTab('history');
                        else navigate('/user-dashboard');
                    }}
                >
                    <History size={18} /> 预测记录
                </button>
                <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} />
                <button 
                    className={`${styles.navItem} ${isConsultation ? styles.active : ''}`} 
                    onClick={() => navigate('/consultation')}
                >
                    <Bot size={18} /> 智能问诊
                </button>
                <button 
                    className={`${styles.navItem} ${isCommunity ? styles.active : ''}`} 
                    onClick={() => navigate('/community')}
                >
                    <MessageSquare size={18} /> 问答社区
                </button>
            </nav>

            <div className={styles.userProfile}>
                <div className={styles.userInfo}>
                    <UserIcon size={20} color="#64748b" />
                    <span className={styles.username}>{username}</span>
                </div>
                <button onClick={handleLogout} className={styles.logoutBtn} title="退出登录">
                    <LogOut size={16} />
                </button>
            </div>
        </aside>
    );
};

export default UserSidebar;
