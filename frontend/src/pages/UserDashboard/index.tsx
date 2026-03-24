import { useState } from 'react';
import { History as HistoryIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './UserDashboard.module.css';
import { useBoneAgeHistory } from './hooks/useBoneAgeHistory';
import { usePredictionWorkspace } from './hooks/usePredictionWorkspace';
import type { PredictionResult } from './types';
import {
  USER_DASHBOARD_DEFAULT_TAB,
  type UserDashboardTab,
} from './tabsConfig';
import RecentHistoryPanel from './components/RecentHistoryPanel';
import UserDashboardContent from './components/UserDashboardContent';
import UserSidebar from './components/UserSidebar';

export default function UserDashboard() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const [jointResult, setJointResult] = useState<PredictionResult | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<UserDashboardTab>(USER_DASHBOARD_DEFAULT_TAB);

  const boneAgeHistory = useBoneAgeHistory();
  const predictionWorkspace = usePredictionWorkspace({
    onPredictionSaved: boneAgeHistory.refreshAll,
    onHistoryRestored: () => setShowHistory(false),
  });

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleTabChange = (tab: UserDashboardTab) => {
    if (tab === activeTab) {
      return;
    }

    predictionWorkspace.clearTransientStatus();
    setActiveTab(tab);
  };

  return (
    <div className={styles.dashboardLayout}>
      <UserSidebar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        username={username}
        handleLogout={handleLogout}
      />

      <main className={styles.mainContent}>
        <header className={styles.topHeader}>
          <h2>
            骨龄与发育评估系统 <small className={styles.subVersion}>v2.1</small>
          </h2>
          <button
            type="button"
            className={styles.historyBtn}
            onClick={() => setShowHistory((previous) => !previous)}
          >
            <HistoryIcon size={16} />
            {showHistory ? '收起历史' : '历史记录'}
          </button>
        </header>

        {showHistory ? (
          <RecentHistoryPanel
            history={boneAgeHistory.history}
            onSelect={(item) => {
              void predictionWorkspace.restoreHistoryItem(item);
            }}
          />
        ) : null}

        <div className={styles.viewPort}>
          <UserDashboardContent
            activeTab={activeTab}
            username={username}
            setActiveTab={handleTabChange}
            jointResult={jointResult}
            setJointResult={setJointResult}
            predictionWorkspace={predictionWorkspace}
            boneAgeHistory={boneAgeHistory}
          />
        </div>
      </main>
    </div>
  );
}
