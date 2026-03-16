import React from 'react';
import { Activity, Users, FileText, MessageSquare, Bot, ShieldCheck, User as UserIcon, LogOut } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import styles from '../DoctorDashboard.module.css';
import type { ActiveTab } from '../types';

interface DoctorSidebarProps {
    isSuperAdmin: boolean;
    activeTab?: ActiveTab;
    setActiveTab?: (tab: ActiveTab) => void;
    username: string | null;
    displayRole: string;
    logout: () => void;
    navigate: (path: string) => void;
}

const DoctorSidebar: React.FC<DoctorSidebarProps> = ({
    isSuperAdmin, activeTab, setActiveTab, username, displayRole, logout, navigate: _navigate
}) => {
    const navigate = useNavigate();
    const location = useLocation();

    const isDashboard = location.pathname === '/doctor-dashboard';
    const isConsultation = location.pathname === '/consultation';
    const isCommunity = location.pathname === '/community';

    return (
        <aside className={styles.sidebar}>
            <div className={styles.brand} style={{ cursor: 'pointer' }} onClick={() => navigate('/doctor-dashboard')}>
                <Activity size={24} color="#3b82f6" />
                <span>{isSuperAdmin ? '超级管理员' : '临床医生'}</span>
            </div>
            <nav className={styles.sideNav}>
                <button 
                    className={`${styles.navItem} ${isDashboard && activeTab === 'records' ? styles.active : ''}`} 
                    onClick={() => {
                        if (isDashboard && setActiveTab) setActiveTab('records');
                        else navigate('/doctor-dashboard');
                    }}
                >
                    <Users size={18} /> 患者记录
                </button>
                
                <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} />
                
                <button 
                    className={`${styles.navItem} ${isConsultation ? styles.active : ''}`} 
                    onClick={() => navigate('/consultation')}
                >
                    <Bot size={18} /> AI 助手
                </button>
                
                <button 
                    className={`${styles.navItem} ${isCommunity ? styles.active : ''}`} 
                    onClick={() => navigate('/community')}
                >
                    <MessageSquare size={18} /> 问答社区
                </button>

                <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} />

                {isSuperAdmin && (
                    <button 
                        className={`${styles.navItem} ${isDashboard && activeTab === 'accounts' ? styles.active : ''}`} 
                        onClick={() => {
                            if (isDashboard && setActiveTab) setActiveTab('accounts');
                            else navigate('/doctor-dashboard');
                        }}
                    >
                        <ShieldCheck size={18} /> 账号管理
                    </button>
                )}
            </nav>
            <div className={styles.userProfile}>
                <div className={styles.userInfo}>
                    <UserIcon size={20} color="#cbd5e1" />
                    <div style={{ overflow: 'hidden' }}>
                        <span className={styles.username} style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', display: 'block' }}>{username}</span>
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
