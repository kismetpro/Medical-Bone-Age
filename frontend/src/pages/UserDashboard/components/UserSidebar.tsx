import { LogOut, User as UserIcon } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import styles from '../UserDashboard.module.css';
import { USER_DASHBOARD_TABS, type UserDashboardTab } from '../tabsConfig';

interface UserSidebarProps {
  activeTab?: UserDashboardTab;
  setActiveTab?: (tab: UserDashboardTab) => void;
  username: string | null;
  handleLogout: () => void;
}

export default function UserSidebar({
  activeTab,
  setActiveTab,
  username,
  handleLogout,
}: UserSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isDashboard = location.pathname === '/user-dashboard';
  const BrandIcon = USER_DASHBOARD_TABS[0].icon;

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand} style={{ cursor: 'pointer' }} onClick={() => navigate('/user-dashboard')}>
        <BrandIcon size={24} color="#3b82f6" />
        <span>患者控制台</span>
      </div>

      <nav className={styles.sideNav}>
        {USER_DASHBOARD_TABS.map((tab, index) => {
          const Icon = tab.icon;
          const showDivider = index > 0 && USER_DASHBOARD_TABS[index - 1].group !== tab.group;

          return (
            <div key={tab.id}>
              {showDivider ? <hr style={{ margin: '0.5rem 0', opacity: 0.1 }} /> : null}
              <button
                type="button"
                className={`${styles.navItem} ${isDashboard && activeTab === tab.id ? styles.active : ''}`}
                onClick={() => {
                  if (isDashboard && setActiveTab) {
                    setActiveTab(tab.id);
                    return;
                  }

                  if (setActiveTab) {
                    setActiveTab(tab.id);
                  }
                  navigate('/user-dashboard');
                }}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            </div>
          );
        })}
      </nav>

      <div className={styles.userProfile}>
        <div className={styles.userInfo}>
          <UserIcon size={20} color="#64748b" />
          <span className={styles.username}>{username}</span>
        </div>
        <button type="button" onClick={handleLogout} className={styles.logoutBtn} title="退出登录">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
