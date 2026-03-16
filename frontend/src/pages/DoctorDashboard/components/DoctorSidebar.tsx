import React from 'react';
import { Activity, Users, FileText, CheckCircle, Bot, ShieldCheck, User as UserIcon, LogOut } from 'lucide-react';
import styles from '../DoctorDashboard.module.css';
import type { ActiveTab } from '../types';

interface DoctorSidebarProps {
    isSuperAdmin: boolean;
    activeTab: ActiveTab;
    setActiveTab: (tab: ActiveTab) => void;
    username: string | null;
    displayRole: string;
    logout: () => void;
    navigate: (path: string) => void;
}

const DoctorSidebar: React.FC<DoctorSidebarProps> = ({
    isSuperAdmin, activeTab, setActiveTab, username, displayRole, logout, navigate
}) => {
    return (
        <aside className={styles.sidebar}>
            <div className={styles.brand}>
                <Activity size={24} color="#3b82f6" />
                <span>{isSuperAdmin ? '超级管理员工作台' : '临床医生工作台'}</span>
            </div>
            <nav className={styles.sideNav}>
                <button className={`${styles.navItem} ${activeTab === 'records' ? styles.active : ''}`} onClick={() => setActiveTab('records')}><Users size={18} />患者记录</button>
                <button className={`${styles.navItem} ${activeTab === 'articles' ? styles.active : ''}`} onClick={() => setActiveTab('articles')}><FileText size={18} />健康科普</button>
                <button className={`${styles.navItem} ${activeTab === 'qa' ? styles.active : ''}`} onClick={() => setActiveTab('qa')}><CheckCircle size={18} />问答回复</button>
                <button className={`${styles.navItem} ${activeTab === 'ai' ? styles.active : ''}`} onClick={() => setActiveTab('ai')}><Bot size={18} />AI 助手</button>
                {isSuperAdmin && <button className={`${styles.navItem} ${activeTab === 'accounts' ? styles.active : ''}`} onClick={() => setActiveTab('accounts')}><ShieldCheck size={18} />账号管理</button>}
            </nav>
            <div className={styles.userProfile}>
                <div className={styles.userInfo}>
                    <UserIcon size={20} color="#cbd5e1" />
                    <div>
                        <span className={styles.username}>{username}</span>
                        <span className={styles.roleBadge}>{displayRole}</span>
                    </div>
                </div>
                <button onClick={() => { logout(); navigate('/'); }} className={styles.logoutBtn} title="退出登录">
                    <LogOut size={16} />
                </button>
            </div>
        </aside>
    );
};

export default DoctorSidebar;
