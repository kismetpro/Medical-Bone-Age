import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from '../../config';
import { useAuth, type AuthRole } from '../../context/AuthContext';
import {
  getHighConfidenceFractures,
  normalizePredictionResult,
  resolveForeignObjectDetection,
  submitPredictionRequest,
} from '../../lib/prediction';
import { buildAuthHeaders, readErrorMessage } from '../../lib/api';
import styles from './DoctorDashboard.module.css';

// --- Types ---
import type { 
    PredictionRecord, PredictionDetail, PatientUser, ManagedAccount 
} from './types';
import type { 
    ActiveTab
} from './types';
import type { PredictionResult, ImageSettings } from '../UserDashboard/types';
import { DEFAULT_SETTINGS } from '../UserDashboard/types';

// --- Components ---
import DoctorSidebar from './components/DoctorSidebar';
import RecordsTab from './components/RecordsTab';
import AccountsTab from './components/AccountsTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';
import { PredictionModal, DetailModal } from './components/Modals';
import DoctorSettingsTab from './components/DoctorSettingsTab';
import DoctorImagePreprocessingTab from './components/DoctorImagePreprocessingTab';
import PredictTab from '../UserDashboard/components/PredictTab';
import JointGradeTab from '../UserDashboard/components/JointGradeTab';
import FormulaMethodTab from '../UserDashboard/components/FormulaMethodTab';
import ManualGradeTab from '../UserDashboard/components/ManualGradeTab';

export default function DoctorDashboard() {
  const { username, role, logout } = useAuth();
  const navigate = useNavigate();
  const isSuperAdmin = role === 'super_admin';
  const displayRole = isSuperAdmin ? '超级管理员' : '临床医生';
  const predictionFileInputRef = useRef<HTMLInputElement>(null);
  const predictTabFileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<ActiveTab>('records');
  const [predictResult, setPredictResult] = useState<PredictionResult | null>(null);
  const [jointResult, setJointResult] = useState<PredictionResult | null>(null);
  const [predictFile, setPredictFile] = useState<File | null>(null);
  const [predictPreview, setPredictPreview] = useState<string | null>(null);
  const [predictGender, setPredictGender] = useState<string>('male');
  const [predictRealAge, setPredictRealAge] = useState<string>('');
  const [predictCurrentHeight, setPredictCurrentHeight] = useState<string>('');
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);
  const [predictImgSettings, setPredictImgSettings] = useState<ImageSettings>(DEFAULT_SETTINGS);
  const [predictionImageSource, setPredictionImageSource] = useState<'upload' | 'preprocessing' | 'history' | null>(null);
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

//   useEffect(() => {
//     if (isSuperAdmin && activeTab === 'accounts') {
//       void fetchAccounts();
//     } else if (activeTab === 'accounts') {
//       setActiveTab('records');
//     }
//   }, [activeTab, isSuperAdmin]);
// 这里的逻辑：监听 Tab 切换，并自动“搬运”数据
useEffect(() => {
  // 1. 原有的超级管理员逻辑（保持不变）
//   if (isSuperAdmin && activeTab === 'accounts') {
//     void fetchAccounts();
//   } else if (activeTab === 'accounts') {
//     setActiveTab('records');
//   }

  // 2. 【新增】临床医生的“小关节识别”与“公式法”数据搬运逻辑
  // 定义哪些 Tab 需要用到 jointResult 数据
//   const medicalTabs: ActiveTab[] = ['joint-grade', 'formula', 'manual-grade'];
//
//   if (medicalTabs.includes(activeTab)) {
//     // 如果“餐盘”是空的，但“仓库”里有刚才点开的病例数据
// //     if (!jointResult && selectedRecord) {
// //       // 核心动作：把数据搬过去，组件瞬间就能渲染了
// //       setJointResult(selectedRecord as unknown as PredictionResult);
// //       console.log("已自动为医生端同步小关节识别数据");
// //     }
// //     // 如果仓库也是空的（医生没选病人就直接点 Tab）
// //     else if (!jointResult ) {
// //       // 引导医生回列表页选病人
// //       setPredictionMessage({ type: 'error', text: '请先在记录列表中点击“查看”或“评估”一个病例。' });
// //       setActiveTab('records');
// //     }
// //   }
// }, [activeTab, isSuperAdmin, selectedRecord, jointResult]); // 必须监听这四个变量
// useEffect(() => {
  // 1. 超级管理员：账号管理逻辑
  if (isSuperAdmin && activeTab === 'accounts') {
    void fetchAccounts();
  } else if (activeTab === 'accounts') {
    setActiveTab('records'); // 越权拦截，踢回记录页
  }

  // 2. 医生端：小关节识别与评估逻辑
  const medicalTabs: ActiveTab[] = ['joint-grade', 'formula', 'manual-grade'];

  if (medicalTabs.includes(activeTab)) {
    // 【关键】只有当“仓库”里有选中的病例，且“组件”还没收到数据时，才执行搬运
    if (selectedRecord && !jointResult) {
      setJointResult(selectedRecord as unknown as PredictionResult);
      console.log("数据已自动同步到评估 Tab");
    }

    // 【注意】不要在这里写任何 setActiveTab('records')
    // 这样即便数据没加载出来，页面也只是停留在当前 Tab 显示“暂无数据”
    // 而不会因为逻辑判断还没跑完就把你强制踢走
  }
}, [activeTab, isSuperAdmin, selectedRecord, jointResult]);

  useEffect(() => () => {
    if (predictionPreview) {
      URL.revokeObjectURL(predictionPreview);
    }
  }, [predictionPreview]);

  useEffect(() => () => {
    if (predictPreview?.startsWith('blob:')) {
      URL.revokeObjectURL(predictPreview);
    }
  }, [predictPreview]);

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

  const syncPredictResult = (
    prediction: PredictionResult | PredictionDetail,
    imageSource: 'upload' | 'preprocessing' | 'history' | null = 'history',
  ) => {
    setPredictResult(prediction as PredictionResult);
    setPredictGender(prediction.gender || 'male');
    setPredictRealAge(prediction.real_age_years != null ? String(prediction.real_age_years) : '');
    setPredictCurrentHeight('');
    setPredictionImageSource(imageSource);
    setPredictError(null);
    setPredictImgSettings(DEFAULT_SETTINGS);
  };

  const getBoxStyle = (coord: number[]): React.CSSProperties => {
    const [xc, yc, w, h] = coord;
    return {
      left: `${(xc - w / 2) * 100}%`,
      top: `${(yc - h / 2) * 100}%`,
      width: `${w * 100}%`,
      height: `${h * 100}%`,
      position: 'absolute',
      border: '2px solid red',
      pointerEvents: 'none',
    };
  };

  const parseAnomalies = (data: PredictionResult | null) => ({
    fractures: getHighConfidenceFractures(data?.anomalies),
    foreign_objects: resolveForeignObjectDetection(data).items,
  });

  const generateMedicalReport = (data: PredictionResult | null) => {
    if (!data) return '分析中...';
    const { predicted_age_years, gender } = data;
    const parsed = parseAnomalies(data);

    let report = `【影像学分析报告】\n`;
    report += `1. 基本信息：受检者性别为${gender === 'male' ? '男' : '女'}，`;
    report += `测定骨龄约为 ${predicted_age_years.toFixed(1)} 岁。\n\n`;
    report += `2. 影像发现：\n`;
    if (parsed.fractures.length > 0) {
      report += `   - [警告] 在影像中识别到 ${parsed.fractures.length} 处疑似骨折区域。建议临床结合压痛点进一步核实。\n`;
    } else {
      report += `   - 骨骼连续性尚好，未见明显骨折征象。\n`;
    }
    if (parsed.foreign_objects.length > 0) {
      report += `   - 注意：影像中存在 ${parsed.foreign_objects.length} 处高密度异物，可能影响骨龄判断。\n`;
    }
    report += `\n3. 结论建议：\n`;
    report += parsed.fractures.length > 0 ? `   结论：疑似存在外伤性改变。` : `   结论：骨龄发育符合当前生理阶段。`;
    return report;
  };

  const getEvaluation = (boneAge: number, chronoAge: number) => {
    const diff = boneAge - chronoAge;
    if (diff > 1) return { status: '早熟 (Advanced)', color: '#ef4444', desc: '骨龄显著大于生活年龄' };
    if (diff < -1) return { status: '晚熟 (Delayed)', color: '#3b82f6', desc: '骨龄显著小于生活年龄' };
    return { status: '正常 (Normal)', color: '#22c55e', desc: '骨龄与生活年龄基本一致' };
  };

  const generateComparisonData = (res: PredictionResult) => {
    if (!res.real_age_years) return [];
    return [
      { name: '实际年龄', age: res.real_age_years, fill: '#94a3b8' },
      { name: '预测骨龄', age: res.predicted_age_years, fill: getEvaluation(res.predicted_age_years, res.real_age_years).color },
    ];
  };

  const loadPredictFile = (file: File) => {
    setPredictFile(file);
    setPredictPreview((previous) => {
      if (previous?.startsWith('blob:')) {
        URL.revokeObjectURL(previous);
      }
      return URL.createObjectURL(file);
    });
    setPredictResult(null);
    setPredictError(null);
    setPredictImgSettings(DEFAULT_SETTINGS);
    setPredictionImageSource('upload');
  };

  const handlePredictFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0];
    if (nextFile) loadPredictFile(nextFile);
  };

  const handlePredictDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const nextFile = event.dataTransfer.files?.[0];
    if (nextFile) loadPredictFile(nextFile);
  };

  const handlePredictSubmit = async () => {
    if (!predictFile) return;
    setPredictLoading(true);
    setPredictError(null);

    try {
      const data = await submitPredictionRequest({
        file: predictFile,
        gender: predictGender,
        currentHeight: predictCurrentHeight,
        realAge: predictRealAge,
        preprocessingEnabled: predictImgSettings.usePreprocessing,
        brightness: predictImgSettings.brightness - 100,
        contrast: predictImgSettings.contrast,
        headers: buildAuthHeaders(),
      });
      const normalized = normalizePredictionResult<PredictionResult>(data, predictRealAge);
      syncPredictResult(normalized, predictionImageSource ?? 'upload');
      setJointResult(normalized);
      setPredictionMessage({ type: 'success', text: '骨龄预测完成，结果已同步到医生工作台。' });
      await fetchRecords();
    } catch (error) {
      setPredictError(`预测失败: ${error instanceof Error ? error.message : '请求异常'}`);
    } finally {
      setPredictLoading(false);
    }
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
      const normalized = normalizePredictionResult<PredictionDetail>(data, predictionForm.realAge);
      setSelectedRecord(normalized);
      setJointResult(normalized as unknown as PredictionResult);
      syncPredictResult(normalized, 'history');
      setPredictionMessage({ type: 'success', text: `已为 ${selectedPatient?.username || `UID ${predictionForm.targetUserId}`} 新增预测记录。` });
      closePredictionModal();
      await fetchRecords();
    } catch (error) {
      setPredictionMessage({ type: 'error', text: error instanceof Error ? error.message : '新增预测记录失败' });
    } finally {
      setPredictionSubmitting(false);
    }
  };

//   const viewDetails = async (id: string) => {
//     try {
//       const response = await fetch(`${API_BASE}/predictions/${id}`, { credentials: 'include', headers: buildAuthHeaders() });
//       if (!response.ok) throw new Error(await readErrorMessage(response));
//       const data = await response.json();
//       setSelectedRecord(normalizePredictionResult<PredictionDetail>(data.data, data.data?.real_age_years));
//     } catch (error) {
//       alert(error instanceof Error ? error.message : '加载详情失败');
//     }
//   };

const viewDetails = async (id: string) => {
  try {
    // 1. 发起请求（保留你原有的配置）
    const response = await fetch(`${API_BASE}/predictions/${id}`, {
      credentials: 'include',
      headers: buildAuthHeaders()
    });

    if (!response.ok) throw new Error(await readErrorMessage(response));

    const data = await response.json();

    // 2. 格式化数据
    const normalized = normalizePredictionResult<PredictionDetail>(
      data.data,
      data.data?.real_age_years
    );

    // 3. 【核心修复】同步更新三个状态
    setSelectedRecord(normalized);                // 更新详情弹窗数据
    setJointResult(normalized as any);            // 喂给小关节识别组件
    syncPredictResult(normalized, 'history');     // 喂给骨龄预测组件
    setActiveTab('joint-grade');                  // 自动跳转到评估页面

  } catch (error) {
    // 4. 错误处理
    console.error("加载详情失败:", error);
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
      if (predictResult?.id === record.id) setPredictResult(null);
      if (jointResult?.id === record.id) setJointResult(null);
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

        {activeTab === 'predict' && (
          <PredictTab
            file={predictFile}
            preview={predictPreview}
            imageStyle={{
              filter: `brightness(${predictImgSettings.brightness}%) contrast(${predictImgSettings.contrast}) ${predictImgSettings.invert ? 'invert(1)' : ''}`,
              transform: `scale(${predictImgSettings.scale / 100})`,
              transition: 'filter 0.2s ease, transform 0.2s ease',
              maxWidth: '100%',
              borderRadius: '8px',
            }}
            imgSettings={predictImgSettings}
            setImgSettings={setPredictImgSettings}
            handleDrop={handlePredictDrop}
            fileInputRef={predictTabFileInputRef}
            handleFileChange={handlePredictFileChange}
            loading={predictLoading}
            gender={predictGender}
            setGender={setPredictGender}
            realAge={predictRealAge}
            setRealAge={setPredictRealAge}
            currentHeight={predictCurrentHeight}
            setCurrentHeight={setPredictCurrentHeight}
            handleSubmit={handlePredictSubmit}
            error={predictError}
            result={predictResult}
            imageSource={predictionImageSource}
            getBoxStyle={(coord) => {
              if (Array.isArray(coord) && coord.length >= 4) {
                return getBoxStyle(coord);
              }
              return { display: 'none' };
            }}
            generateMedicalReport={(data) => {
              try { return generateMedicalReport(data); }
              catch (_error) { return '报告计算中或数据暂缺...'; }
            }}
            generateComparisonData={generateComparisonData}
            getEvaluation={getEvaluation}
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

        {activeTab === 'joint-grade' &&(
          <JointGradeTab 
            result={jointResult}
            setResult={setJointResult}
          />
        )}

        {activeTab === 'formula'  &&(
          <FormulaMethodTab 
            result={jointResult}
            setResult={setJointResult}
          />
        )}

        {activeTab === 'manual-grade'  && (
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
