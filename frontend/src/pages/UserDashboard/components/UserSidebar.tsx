import React from 'react';
import { Activity, History, FileSpreadsheet, LogOut, User as UserIcon } from 'lucide-react';
import styles from '../UserDashboard.module.css';

interface UserSidebarProps {
    activeTab: 'predict' | 'history' | 'community';
    setActiveTab: (tab: 'predict' | 'history' | 'community') => void;
    username: string | null;
    handleLogout: () => void;
}

const UserSidebar: React.FC<UserSidebarProps> = ({ activeTab, setActiveTab, username, handleLogout }) => {
    return (
        <aside className={styles.sidebar}>
            <div className={styles.brand}>
                <Activity size={24} color="#3b82f6" />
                <span>患者控制台</span>
            </div>

            <nav className={styles.sideNav}>
                <button 
                    className={`${styles.navItem} ${activeTab === 'predict' ? styles.active : ''}`} 
                    onClick={() => setActiveTab('predict')}
                >
                    <Activity size={18} /> 预测评估
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'history' ? styles.active : ''}`} 
                    onClick={() => setActiveTab('history')}
                >
                    <History size={18} /> 预测记录
                </button>
                <button 
                    className={`${styles.navItem} ${activeTab === 'community' ? styles.active : ''}`} 
                    onClick={() => setActiveTab('community')}
                >
                    <FileSpreadsheet size={18} /> 社区与科普
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
