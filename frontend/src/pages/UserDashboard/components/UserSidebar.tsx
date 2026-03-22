import React from 'react';
import { Activity, History as HistoryIcon, MessageSquare, Bot, User as UserIcon, LogOut, Bone, Settings, Image as ImageIcon, Calculator, Edit3 } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import styles from '../UserDashboard.module.css';

interface UserSidebarProps {
    activeTab?: 'predict' | 'history' | 'community' | 'consultation' | 'joint-grade' | 'settings' | 'preprocessing' | 'formula' | 'manual-grade';
    setActiveTab?: (tab: 'predict' | 'history' | 'community' | 'consultation' | 'joint-grade' | 'settings' | 'preprocessing' | 'formula' | 'manual-grade') => void;
    username: string | null;
    handleLogout: () => void;
}

const UserSidebar: React.FC<UserSidebarProps> = ({ activeTab, setActiveTab, username, handleLogout }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const isDashboard = location.pathname === '/user-dashboard';

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
                    <HistoryIcon size={18} /> 预测记录
                </button>
                <button 
                    className={`${styles.navItem} ${isDashboard && activeTab === 'joint-grade' ? styles.active : ''}`} 
                    onClick={() => {
                        if (isDashboard && setActiveTab) setActiveTab('joint-grade');
                        else navigate('/user-dashboard');
                    }}
                >
                    <Bone size={18} /> 小关节分级
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'formula' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('formula');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <Calculator size={18} /> 公式法预测骨龄
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'manual-grade' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('manual-grade');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <Edit3 size={18} /> 手动分级计算
                </button>
                <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} />
                <button 
                    className={`${styles.navItem} ${activeTab === 'consultation' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('consultation');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <Bot size={18} /> 智能问诊
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'community' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('community');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <MessageSquare size={18} /> 问答社区
                </button>
                <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} />
                <button 
                    className={`${styles.navItem} ${activeTab === 'preprocessing' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('preprocessing');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <ImageIcon size={18} /> 图像预处理
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'settings' ? styles.active : ''}`} 
                    onClick={() => {
                        if (setActiveTab) setActiveTab('settings');
                        if (!isDashboard) navigate('/user-dashboard');
                    }}
                >
                    <Settings size={18} /> 系统设置
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