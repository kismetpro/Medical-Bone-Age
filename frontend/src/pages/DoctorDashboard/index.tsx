import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from '../../config';
import { useAuth, type AuthRole } from '../../context/AuthContext';
import { normalizePredictionResult, submitPredictionRequest } from '../../lib/prediction';
import { buildAuthHeaders, readErrorMessage } from '../../lib/api';
import styles from './DoctorDashboard.module.css';

// --- Types ---
import type { 
    PredictionRecord, PredictionDetail, PatientUser, ManagedAccount 
} from './types';
import type { 
    ActiveTab
} from './types';
import type { PredictionResult } from '../UserDashboard/types';

// --- Components ---
import DoctorSidebar from './components/DoctorSidebar';
import RecordsTab from './components/RecordsTab';
import AccountsTab from './components/AccountsTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';
import { PredictionModal, DetailModal } from './components/Modals';
import DoctorSettingsTab from './components/DoctorSettingsTab';
import DoctorImagePreprocessingTab from './components/DoctorImagePreprocessingTab';
import JointGradeTab from '../UserDashboard/components/JointGradeTab';
import FormulaMethodTab from '../UserDashboard/components/FormulaMethodTab';
import ManualGradeTab from '../UserDashboard/components/ManualGradeTab';

export default function DoctorDashboard() {
  const { username, role, logout } = useAuth();
  const navigate = useNavigate();
  const isSuperAdmin = role === 'super_admin';
  const displayRole = isSuperAdmin ? '超级管理员' : '临床医生';
  const predictionFileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<ActiveTab>('records');
  const [jointResult, setJointResult] = useState<PredictionResult | null>(null);
  const [records, setRecords] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<PredictionDetail | null>(null);
  const [patientUsers, setPatientUsers] = useState<PatientUser[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(false);
  const [predictionModalOpen, setPredictionModalOpen] = useState(false);
  const [predictionForm, setPredictionForm] = useState<{ 
    targetUserId: string; 
    gender: 'male' | 'female'; 
    currentHeight: string; 
    realAge: string;
    preprocessingEnabled: boolean;
    brightness: number;
    contrast: number;
  }>({ 
    targetUserId: '', 
    gender: 'male', 
    currentHeight: '', 
    realAge: '',
    preprocessingEnabled: false,
    brightness: 100,
    contrast: 13.24
  });
  const [predictionFile, setPredictionFile] = useState<File | null>(null);
  const [predictionPreview, setPredictionPreview] = useState<string | null>(null);
  const [predictionSubmitting, setPredictionSubmitting] = useState(false);
  const [predictionMutationId, setPredictionMutationId] = useState<string | null>(null);
  const [predictionMessage, setPredictionMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);
  const [accounts, setAccounts] = useState<ManagedAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountNotice, setAccountNotice] = useState<string | null>(null);
  const [accountMutationId, setAccountMutationId] = useState<number | null>(null);
  const [newAccount, setNewAccount] = useState({ username: '', password: '', role: 'user' as AuthRole });

  useEffect(() => {
    void fetchRecords();
    void fetchPatientUsers();
  }, []);

  useEffect(() => {
    if (isSuperAdmin && activeTab === 'accounts') {
      void fetchAccounts();
    } else if (activeTab === 'accounts') {
      setActiveTab('records');
    }
  }, [activeTab, isSuperAdmin]);

  useEffect(() => () => {
    if (predictionPreview) {
      URL.revokeObjectURL(predictionPreview);
    }
  }, [predictionPreview]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/predictions`, { credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setRecords(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      setPredictionMessage({ type: 'error', text: error instanceof Error ? error.message : '加载预测记录失败' });
    } finally {
      setLoading(false);
    }
  };

  const fetchPatientUsers = async () => {
    setPatientsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/doctor/patient-users`, { credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setPatientUsers(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      setPredictionMessage({ type: 'error', text: error instanceof Error ? error.message : '加载个人用户列表失败' });
    } finally {
      setPatientsLoading(false);
    }
  };

  const fetchAccounts = async () => {
    if (!isSuperAdmin) return;
    setAccountsLoading(true);
    setAccountError(null);
    try {
      const response = await fetch(`${API_BASE}/auth/users`, { credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setAccounts(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '加载账号列表失败');
    } finally {
      setAccountsLoading(false);
    }
  };

  const closePredictionModal = () => {
    setPredictionModalOpen(false);
    setPredictionFile(null);
    setPredictionForm({ 
      targetUserId: '', 
      gender: 'male', 
      currentHeight: '', 
      realAge: '',
      preprocessingEnabled: false,
      brightness: 100,
      contrast: 13.24 
    });
    setPredictionPreview((previous) => {
      if (previous) URL.revokeObjectURL(previous);
      return null;
    });
  };

  const loadPredictionFile = (file: File) => {
    setPredictionFile(file);
    setPredictionPreview((previous) => {
      if (previous) URL.revokeObjectURL(previous);
      return URL.createObjectURL(file);
    });
  };

  const createPrediction = async () => {
    if (!predictionForm.targetUserId) return setPredictionMessage({ type: 'error', text: '请先选择一个个人用户。' });
    if (!predictionFile) return setPredictionMessage({ type: 'error', text: '请上传需要预测的X光影像。' });
    setPredictionSubmitting(true);
    setPredictionMessage(null);
    try {
      const data = await submitPredictionRequest({
        file: predictionFile,
        gender: predictionForm.gender,
        currentHeight: predictionForm.currentHeight,
        realAge: predictionForm.realAge,
        targetUserId: Number(predictionForm.targetUserId),
        preprocessingEnabled: predictionForm.preprocessingEnabled,
        brightness: predictionForm.brightness - 100,
        contrast: predictionForm.contrast,
        headers: buildAuthHeaders(),
      });
      const selectedPatient = patientUsers.find((item) => String(item.id) === predictionForm.targetUserId);
      setSelectedRecord(normalizePredictionResult<PredictionDetail>(data, predictionForm.realAge));
      setPredictionMessage({ type: 'success', text: `已为 ${selectedPatient?.username || `UID ${predictionForm.targetUserId}`} 新增预测记录。` });
      closePredictionModal();
      await fetchRecords();
    } catch (error) {
      setPredictionMessage({ type: 'error', text: error instanceof Error ? error.message : '新增预测记录失败' });
    } finally {
      setPredictionSubmitting(false);
    }
  };

  const viewDetails = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/predictions/${id}`, { credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setSelectedRecord(normalizePredictionResult<PredictionDetail>(data.data, data.data?.real_age_years));
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载详情失败');
    }
  };

  const deletePredictionRecord = async (record: PredictionRecord) => {
    if (!window.confirm(`确认删除 ${record.username || `UID ${record.user_id}`} 的这条预测记录吗？相关联骨龄点位也会被删除。`)) return;
    setPredictionMutationId(record.id);
    setPredictionMessage(null);
    try {
      const response = await fetch(`${API_BASE}/predictions/${record.id}`, { method: 'DELETE', credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      if (selectedRecord?.id === record.id) setSelectedRecord(null);
      setPredictionMessage({ type: 'success', text: `预测记录 #${record.id.slice(0, 8)} 已删除。` });
      await fetchRecords();
    } catch (error) {
      setPredictionMessage({ type: 'error', text: error instanceof Error ? error.message : '删除预测记录失败' });
    } finally {
      setPredictionMutationId(null);
    }
  };

  const createAccount = async () => {
    if (!newAccount.username.trim() || !newAccount.password.trim()) return setAccountError('用户名和密码不能为空。');
    setAccountsLoading(true);
    setAccountError(null);
    setAccountNotice(null);
    try {
      const response = await fetch(`${API_BASE}/auth/users`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify(newAccount),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      setNewAccount({ username: '', password: '', role: 'user' });
      setAccountNotice(`账号 ${newAccount.username} 创建成功。`);
      await fetchAccounts();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '创建账号失败');
    } finally {
      setAccountsLoading(false);
    }
  };

  const updateAccountRole = async (account: ManagedAccount, nextRole: AuthRole) => {
    if (account.role === nextRole) return;
    setAccountMutationId(account.id);
    setAccountError(null);
    setAccountNotice(null);
    try {
      const response = await fetch(`${API_BASE}/auth/users/${account.id}/role`, {
        method: 'PATCH',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify({ role: nextRole }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      setAccountNotice(`已将 ${account.username} 调整为 ${nextRole}。`);
      await fetchAccounts();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '修改权限失败');
    } finally {
      setAccountMutationId(null);
    }
  };

  const deleteAccount = async (account: ManagedAccount) => {
    if (!window.confirm(`确认删除账号 ${account.username} 吗？相关数据也会一并删除。`)) return;
    setAccountMutationId(account.id);
    setAccountError(null);
    setAccountNotice(null);
    try {
      const response = await fetch(`${API_BASE}/auth/users/${account.id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      setAccountNotice(`账号 ${account.username} 已删除。`);
      await fetchAccounts();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '删除账号失败');
    } finally {
      setAccountMutationId(null);
    }
  };

  return (
    <div className={styles.dashboardLayout}>
      <DoctorSidebar 
        isSuperAdmin={isSuperAdmin}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        username={username}
        displayRole={displayRole}
        logout={logout}
        navigate={navigate}
      />

      <main className={styles.mainContent}>
        <header className={styles.topHeader}><h2>{isSuperAdmin ? '超级管理员工作台' : '临床医生工作台'}</h2></header>
        
        {predictionMessage && <div className={`${styles.noticeBanner} ${predictionMessage.type === 'error' ? styles.noticeError : styles.noticeSuccess}`}>{predictionMessage.text}</div>}

        {activeTab === 'records' && (
          <RecordsTab 
            records={records}
            patientUsers={patientUsers}
            displayRole={displayRole}
            loading={loading}
            patientsLoading={patientsLoading}
            fetchRecords={fetchRecords}
            fetchPatientUsers={fetchPatientUsers}
            setPredictionModalOpen={setPredictionModalOpen}
            viewDetails={viewDetails}
            deletePredictionRecord={deletePredictionRecord}
            predictionMutationId={predictionMutationId}
          />
        )}

        {activeTab === 'accounts' && isSuperAdmin && (
          <AccountsTab 
            newAccount={newAccount}
            setNewAccount={setNewAccount}
            createAccount={createAccount}
            accountsLoading={accountsLoading}
            accountError={accountError}
            accountNotice={accountNotice}
            fetchAccounts={fetchAccounts}
            accounts={accounts}
            username={username}
            accountMutationId={accountMutationId}
            updateAccountRole={updateAccountRole}
            deleteAccount={deleteAccount}
          />
        )}

        {activeTab === 'consultation' && <ConsultationPage />}
        {activeTab === 'community' && <CommunityPage />}
        
        {activeTab === 'settings' && (
          <DoctorSettingsTab 
            username={username}
            isSuperAdmin={isSuperAdmin}
            onUpdateSuccess={() => {
              console.log('设置已更新');
            }}
          />
        )}

        {activeTab === 'preprocessing' && (
          <DoctorImagePreprocessingTab 
            username={username}
          />
        )}

        {activeTab === 'joint-grade' && isSuperAdmin && (
          <JointGradeTab 
            result={jointResult}
            setResult={setJointResult}
          />
        )}

        {activeTab === 'formula' && isSuperAdmin && (
          <FormulaMethodTab 
            result={jointResult}
            setResult={setJointResult}
          />
        )}

        {activeTab === 'manual-grade' && isSuperAdmin && (
          <ManualGradeTab 
            result={jointResult}
            setResult={setJointResult}
          />
        )}
      </main>

      {predictionModalOpen && (
        <PredictionModal 
          closePredictionModal={closePredictionModal}
          predictionForm={predictionForm}
          setPredictionForm={setPredictionForm}
          patientsLoading={patientsLoading}
          patientUsers={patientUsers}
          createPrediction={createPrediction}
          predictionSubmitting={predictionSubmitting}
          predictionFileInputRef={predictionFileInputRef}
          loadPredictionFile={loadPredictionFile}
          predictionPreview={predictionPreview}
          predictionFile={predictionFile}
        />
      )}

      {selectedRecord && (
        <DetailModal 
          selectedRecord={selectedRecord}
          setSelectedRecord={setSelectedRecord}
        />
      )}
    </div>
  );
}
