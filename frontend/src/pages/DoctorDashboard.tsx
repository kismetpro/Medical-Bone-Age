import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Bot,
  CheckCircle,
  Eye,
  FileText,
  LogOut,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  Upload,
  User as UserIcon,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { API_BASE } from '../config';
import { useAuth, type AuthRole } from '../context/AuthContext';
import { normalizePredictionResult, submitPredictionRequest } from '../lib/prediction';
import styles from './DoctorDashboard.module.css';

interface PredictionRecord { id: string; user_id: number; username?: string; timestamp: number; filename: string; predicted_age_years: number; gender: string; }
interface PredictionDetail extends PredictionRecord { real_age_years?: number; predicted_adult_height?: number; anomalies?: Array<{ type: string; score: number; coord: number[] }>; heatmap_base64?: string; rus_chn_details?: { total_score?: number }; }
interface PatientUser { id: number; username: string; created_at: string; }
interface QaItem { qid: number; owner: string; text: string; image: string; reply: string; createTime: string; }
interface ManagedAccount { id: number; username: string; role: AuthRole; created_at: string; }
type ActiveTab = 'records' | 'articles' | 'qa' | 'ai' | 'accounts';
type ChatMessage = { role: 'user' | 'assistant'; text: string };

const roleLabelMap: Record<AuthRole, string> = { user: '个人用户', doctor: '临床医生', super_admin: '超级管理员' };
const buildAuthHeaders = (json = false) => {
  const token = localStorage.getItem('boneage_token');
  const headers: Record<string, string> = {};
  if (json) headers['Content-Type'] = 'application/json';
  if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) headers.Authorization = `Bearer ${token}`;
  return headers;
};
const readErrorMessage = async (response: Response) => {
  const payload = await response.json().catch(() => ({}));
  return typeof payload.detail === 'string' ? payload.detail : '请求失败';
};

export default function DoctorDashboard() {
  const { username, role, logout } = useAuth();
  const navigate = useNavigate();
  const isSuperAdmin = role === 'super_admin';
  const displayRole = isSuperAdmin ? '超级管理员' : '临床医生';
  const predictionFileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<ActiveTab>('records');
  const [records, setRecords] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<PredictionDetail | null>(null);
  const [patientUsers, setPatientUsers] = useState<PatientUser[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(false);
  const [predictionModalOpen, setPredictionModalOpen] = useState(false);
  const [predictionForm, setPredictionForm] = useState({ targetUserId: '', gender: 'male' as 'male' | 'female', currentHeight: '', realAge: '' });
  const [predictionFile, setPredictionFile] = useState<File | null>(null);
  const [predictionPreview, setPredictionPreview] = useState<string | null>(null);
  const [predictionSubmitting, setPredictionSubmitting] = useState(false);
  const [predictionMutationId, setPredictionMutationId] = useState<string | null>(null);
  const [predictionMessage, setPredictionMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);
  const [newArticle, setNewArticle] = useState({ title: '', content: '' });
  const [qaList, setQaList] = useState<QaItem[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const [replyTexts, setReplyTexts] = useState<Record<number, string>>({});
  const [replySubmitting, setReplySubmitting] = useState<Record<number, boolean>>({});
  const [expandedQid, setExpandedQid] = useState<number | null>(null);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([]);
  const [accounts, setAccounts] = useState<ManagedAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountNotice, setAccountNotice] = useState<string | null>(null);
  const [accountMutationId, setAccountMutationId] = useState<number | null>(null);
  const [newAccount, setNewAccount] = useState({ username: '', password: '', role: 'user' as AuthRole });

  useEffect(() => {
    void fetchRecords();
    void fetchPatientUsers();
    void fetchDoctorQaList();
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

  const fetchDoctorQaList = async () => {
    setQaLoading(true);
    try {
      const response = await fetch(`${API_BASE}/qa/questions`, { credentials: 'include', headers: buildAuthHeaders() });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setQaList(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error(error);
    } finally {
      setQaLoading(false);
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
    setPredictionForm({ targetUserId: '', gender: 'male', currentHeight: '', realAge: '' });
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
      setSelectedRecord(data.data as PredictionDetail);
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

  const replyToQuestion = async (qid: number) => {
    const reply = replyTexts[qid]?.trim();
    if (!reply) return;
    setReplySubmitting((previous) => ({ ...previous, [qid]: true }));
    try {
      const response = await fetch(`${API_BASE}/qa/questions/${qid}/reply`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify({ reply }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      setReplyTexts((previous) => ({ ...previous, [qid]: '' }));
      await fetchDoctorQaList();
    } catch (error) {
      alert(error instanceof Error ? error.message : '提交回复失败');
    } finally {
      setReplySubmitting((previous) => ({ ...previous, [qid]: false }));
    }
  };

  const submitArticle = async () => {
    if (!newArticle.title.trim() || !newArticle.content.trim()) return alert('请填写完整的文章标题和内容。');
    try {
      const response = await fetch(`${API_BASE}/articles`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify(newArticle),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      setNewArticle({ title: '', content: '' });
      alert('科普文章发布成功。');
    } catch (error) {
      alert(error instanceof Error ? error.message : '文章发布失败');
    }
  };

  const askAiAssistant = async () => {
    const message = aiInput.trim();
    if (!message) return;
    setAiLoading(true);
    setAiMessages((previous) => [...previous, { role: 'user', text: message }]);
    setAiInput('');
    try {
      const response = await fetch(`${API_BASE}/doctor/ai-assistant`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify({
          message,
          prediction_id: selectedRecord?.id || undefined,
          context: selectedRecord
            ? { predicted_age_years: selectedRecord.predicted_age_years, gender: selectedRecord.gender, anomalies: selectedRecord.anomalies }
            : undefined,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'AI 助手请求失败');
      setAiMessages((previous) => [...previous, { role: 'assistant', text: data.reply || '未返回内容。' }]);
    } catch (error) {
      setAiMessages((previous) => [...previous, { role: 'assistant', text: `调用失败：${error instanceof Error ? error.message : '未知错误'}` }]);
    } finally {
      setAiLoading(false);
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
      setAccountNotice(`已将 ${account.username} 调整为${roleLabelMap[nextRole]}。`);
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

  const renderAccountsTab = () => (
    <div className={styles.workspaceGrid}>
      <div className={styles.tableCard} style={{ padding: '1.2rem', marginBottom: '1rem' }}>
        <div className={styles.accountFormGrid}>
          <input className={styles.formInput} placeholder="用户名" value={newAccount.username} onChange={(event) => setNewAccount((previous) => ({ ...previous, username: event.target.value }))} />
          <input className={styles.formInput} type="password" placeholder="初始密码" value={newAccount.password} onChange={(event) => setNewAccount((previous) => ({ ...previous, password: event.target.value }))} />
          <select className={styles.formInput} value={newAccount.role} onChange={(event) => setNewAccount((previous) => ({ ...previous, role: event.target.value as AuthRole }))}>
            {Object.entries(roleLabelMap).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <button className={styles.primaryActionBtn} onClick={() => void createAccount()} disabled={accountsLoading}><UserPlus size={16} />新建账号</button>
        </div>
        {(accountError || accountNotice) && <div className={`${styles.noticeBanner} ${accountError ? styles.noticeError : styles.noticeSuccess}`}>{accountError || accountNotice}</div>}
      </div>
      <div className={styles.tableCard}>
        <div className={styles.cardHeader}><h3>账号列表</h3><button className={styles.refreshBtn} onClick={() => void fetchAccounts()} disabled={accountsLoading}><RefreshCw size={16} className={accountsLoading ? 'spin' : ''} />刷新列表</button></div>
        <div className={styles.tableWrapper}><table><thead><tr><th>用户名</th><th>角色</th><th>创建时间</th><th>操作</th></tr></thead><tbody>{accounts.length === 0 ? <tr><td colSpan={4} className={styles.emptyState}>{accountsLoading ? '正在加载账号列表...' : '暂无账号数据'}</td></tr> : accounts.map((account) => { const isSelf = account.username === username; const isLastSuperAdmin = account.role === 'super_admin' && accounts.filter((item) => item.role === 'super_admin').length <= 1; const locked = isSelf || isLastSuperAdmin || accountMutationId === account.id; return <tr key={account.id}><td><div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}><span>{account.username}</span>{isSelf && <span className={styles.selfBadge}>当前账号</span>}</div></td><td><select className={styles.rowSelect} value={account.role} disabled={locked} onChange={(event) => void updateAccountRole(account, event.target.value as AuthRole)}>{Object.entries(roleLabelMap).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></td><td>{new Date(account.created_at).toLocaleString()}</td><td><button className={`${styles.actionBtn} ${styles.dangerBtn}`} onClick={() => void deleteAccount(account)} disabled={locked}><Trash2 size={14} />删除</button></td></tr>; })}</tbody></table></div>
      </div>
    </div>
  );

  const messageNode = predictionMessage && <div className={`${styles.noticeBanner} ${predictionMessage.type === 'error' ? styles.noticeError : styles.noticeSuccess}`}>{predictionMessage.text}</div>;
  const genderLabel = (value: string) => (value === 'male' ? '男' : '女');
  const selectedPatient = patientUsers.find((item) => String(item.id) === predictionForm.targetUserId);

  return (
    <div className={styles.dashboardLayout}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}><Activity size={24} color="#3b82f6" /><span>{isSuperAdmin ? '超级管理员工作台' : '临床医生工作台'}</span></div>
        <nav className={styles.sideNav}>
          <button className={`${styles.navItem} ${activeTab === 'records' ? styles.active : ''}`} onClick={() => setActiveTab('records')}><Users size={18} />患者记录</button>
          <button className={`${styles.navItem} ${activeTab === 'articles' ? styles.active : ''}`} onClick={() => setActiveTab('articles')}><FileText size={18} />健康科普</button>
          <button className={`${styles.navItem} ${activeTab === 'qa' ? styles.active : ''}`} onClick={() => setActiveTab('qa')}><CheckCircle size={18} />问答回复</button>
          <button className={`${styles.navItem} ${activeTab === 'ai' ? styles.active : ''}`} onClick={() => setActiveTab('ai')}><Bot size={18} />AI 助手</button>
          {isSuperAdmin && <button className={`${styles.navItem} ${activeTab === 'accounts' ? styles.active : ''}`} onClick={() => setActiveTab('accounts')}><ShieldCheck size={18} />账号管理</button>}
        </nav>
        <div className={styles.userProfile}><div className={styles.userInfo}><UserIcon size={20} color="#cbd5e1" /><div><span className={styles.username}>{username}</span><span className={styles.roleBadge}>{displayRole}</span></div></div><button onClick={() => { logout(); navigate('/'); }} className={styles.logoutBtn} title="退出登录"><LogOut size={16} /></button></div>
      </aside>

      <main className={styles.mainContent}>
        <header className={styles.topHeader}><h2>{isSuperAdmin ? '超级管理员工作台' : '临床医生工作台'}</h2></header>
        {messageNode}

        {activeTab === 'records' && <div className={styles.workspaceGrid}><div className={styles.statsGrid}><div className={styles.statCard}><div className={`${styles.statIcon} ${styles.blue}`}><Users size={24} /></div><div className={styles.statInfo}><h4>记录总数</h4><p>{records.length}</p></div></div><div className={styles.statCard}><div className={`${styles.statIcon} ${styles.purple}`}><Activity size={24} /></div><div className={styles.statInfo}><h4>个人用户数</h4><p>{patientUsers.length}</p></div></div><div className={styles.statCard}><div className={`${styles.statIcon} ${styles.green}`}><CheckCircle size={24} /></div><div className={styles.statInfo}><h4>当前角色</h4><p style={{ fontSize: '1rem' }}>{displayRole}</p></div></div></div><div className={styles.tableCard}><div className={styles.cardHeader}><h3>近期预测记录</h3><div className={styles.headerActions}><button className={styles.refreshBtn} onClick={() => void fetchPatientUsers()} disabled={patientsLoading}><RefreshCw size={16} className={patientsLoading ? 'spin' : ''} />刷新用户</button><button className={styles.refreshBtn} onClick={() => void fetchRecords()} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} />刷新列表</button><button className={styles.primaryActionBtn} onClick={() => setPredictionModalOpen(true)}><Upload size={16} />新增预测记录</button></div></div><div className={styles.tableWrapper}><table><thead><tr><th>记录 ID</th><th>日期时间</th><th>个人用户</th><th>用户 ID</th><th>性别</th><th>预测骨龄</th><th>操作</th></tr></thead><tbody>{records.length === 0 ? <tr><td colSpan={7} className={styles.emptyState}>{loading ? '正在加载预测记录...' : '暂无预测记录'}</td></tr> : records.map((record) => <tr key={record.id}><td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', color: '#64748b' }}>#{record.id.slice(0, 8)}</td><td>{new Date(record.timestamp).toLocaleString()}</td><td>{record.username || '未知用户'}</td><td>UID: {record.user_id}</td><td><span className={`${styles.genderTag} ${record.gender === 'male' ? styles.male : styles.female}`}>{genderLabel(record.gender)}</span></td><td style={{ fontWeight: 600 }}>{record.predicted_age_years.toFixed(1)} 岁</td><td><div className={styles.rowActions}><button className={styles.actionBtn} onClick={() => void viewDetails(record.id)}><Eye size={14} />查看详情</button><button className={`${styles.actionBtn} ${styles.dangerBtn}`} onClick={() => void deletePredictionRecord(record)} disabled={predictionMutationId === record.id}><Trash2 size={14} />删除</button></div></td></tr>)}</tbody></table></div></div></div>}

        {activeTab === 'articles' && <div className={styles.workspaceGrid}><div className={styles.tableCard} style={{ padding: '2rem' }}><h3 style={{ margin: '0 0 1.5rem 0' }}>发布科普文章</h3><input className={styles.formInput} style={{ marginBottom: '1rem' }} placeholder="文章标题" value={newArticle.title} onChange={(event) => setNewArticle((previous) => ({ ...previous, title: event.target.value }))} /><textarea className={styles.textareaInput} placeholder="在这里编写文章内容..." value={newArticle.content} onChange={(event) => setNewArticle((previous) => ({ ...previous, content: event.target.value }))} /><button className={styles.primaryActionBtn} style={{ marginTop: '1rem' }} onClick={() => void submitArticle()}>发布文章</button></div></div>}

        {activeTab === 'qa' && <div style={{ padding: '0 0.5rem' }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}><h3 style={{ margin: 0 }}>患者问答</h3><button className={styles.refreshBtn} onClick={() => void fetchDoctorQaList()} disabled={qaLoading}><RefreshCw size={16} className={qaLoading ? 'spin' : ''} />刷新列表</button></div>{qaList.length === 0 && !qaLoading && <p style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem 0' }}>暂无患者提问。</p>}<div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>{qaList.map((question) => <div key={question.qid} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white', overflow: 'hidden' }}><div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer', background: expandedQid === question.qid ? '#f0f7ff' : 'white' }} onClick={() => setExpandedQid(expandedQid === question.qid ? null : question.qid)}><div style={{ flex: 1 }}><div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>患者：<strong>{question.owner}</strong> · {new Date(question.createTime).toLocaleString()}</div><div style={{ fontSize: '0.92rem', color: '#1e293b', lineHeight: 1.4 }}>{question.text}</div></div><span className={question.reply ? styles.successPill : styles.pendingPill}>{question.reply ? '已回复' : '待回复'}</span></div>{expandedQid === question.qid && <div style={{ borderTop: '1px solid #e2e8f0', padding: '1rem' }}>{question.image && <img src={question.image} alt="患者附图" style={{ maxWidth: '280px', maxHeight: '200px', objectFit: 'contain', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '0.85rem' }} />}{question.reply && <div className={styles.replyBox}><strong>已有回复：</strong>{question.reply}</div>}<textarea className={styles.textareaInput} style={{ minHeight: '90px' }} placeholder="请输入专业回复内容..." value={replyTexts[question.qid] || ''} onChange={(event) => setReplyTexts((previous) => ({ ...previous, [question.qid]: event.target.value }))} /><div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}><button className={styles.primaryActionBtn} onClick={() => void replyToQuestion(question.qid)} disabled={replySubmitting[question.qid] || !replyTexts[question.qid]?.trim()}>{replySubmitting[question.qid] ? '提交中...' : question.reply ? '更新回复' : '提交回复'}</button></div></div>}</div>)}</div></div>}

        {activeTab === 'ai' && <div className={styles.workspaceGrid}><div className={styles.tableCard} style={{ padding: '1rem' }}><h3 style={{ margin: '0 0 1rem 0' }}>AI 临床助手</h3><p style={{ margin: '0 0 1rem 0', color: '#64748b' }}>可输入病例分析需求、阅片疑问或后续检查建议，由 AI 提供结构化辅助意见。</p><div style={{ border: '1px solid #e2e8f0', borderRadius: 10, minHeight: 280, maxHeight: 380, overflow: 'auto', padding: '0.75rem', background: '#f8fafc' }}>{aiMessages.length === 0 && <p style={{ color: '#64748b', margin: 0 }}>暂无对话，请先输入问题。</p>}{aiMessages.map((message, index) => <div key={`${message.role}-${index}`} style={{ marginBottom: '0.6rem', padding: '0.6rem 0.7rem', borderRadius: 10, background: message.role === 'user' ? '#dbeafe' : 'white', border: '1px solid #e2e8f0' }}><div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.2rem' }}>{message.role === 'user' ? '你' : 'AI 助手'}</div><div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{message.text}</div></div>)}</div><div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.6rem', marginTop: '0.8rem' }}><textarea className={styles.textareaInput} style={{ minHeight: 90 }} placeholder="例如：请根据当前预测结果给出鉴别诊断建议。" value={aiInput} onChange={(event) => setAiInput(event.target.value)} /><button className={styles.primaryActionBtn} style={{ alignSelf: 'end', minHeight: 42 }} onClick={() => void askAiAssistant()} disabled={aiLoading}><Send size={14} />{aiLoading ? '运行中...' : '发送'}</button></div></div></div>}

        {activeTab === 'accounts' && isSuperAdmin && renderAccountsTab()}
      </main>

      {predictionModalOpen && <div className={styles.modalOverlay}><div className={styles.modalContent}><div className={styles.modalHeader}><h3>新增预测记录</h3><button className={styles.closeBtn} onClick={closePredictionModal}><X size={20} /></button></div><div className={styles.modalBody}><div className={styles.predictionFormGrid}><div><div className={styles.detailBlock}><h4>选择个人用户</h4><select className={styles.formInput} value={predictionForm.targetUserId} onChange={(event) => setPredictionForm((previous) => ({ ...previous, targetUserId: event.target.value }))}><option value="">{patientsLoading ? '正在加载个人用户...' : '请选择个人用户'}</option>{patientUsers.map((patient) => <option key={patient.id} value={patient.id}>{patient.username} (UID: {patient.id})</option>)}</select></div><div className={styles.detailBlock}><h4>性别</h4><div className={styles.genderSwitch}><button type="button" className={predictionForm.gender === 'male' ? styles.genderSwitchActive : ''} onClick={() => setPredictionForm((previous) => ({ ...previous, gender: 'male' }))}>男</button><button type="button" className={predictionForm.gender === 'female' ? styles.genderSwitchActive : ''} onClick={() => setPredictionForm((previous) => ({ ...previous, gender: 'female' }))}>女</button></div></div><div className={styles.predictionInputGrid}><input className={styles.formInput} placeholder="当前身高（cm，可选）" value={predictionForm.currentHeight} onChange={(event) => setPredictionForm((previous) => ({ ...previous, currentHeight: event.target.value }))} /><input className={styles.formInput} placeholder="实际年龄（岁，可选）" value={predictionForm.realAge} onChange={(event) => setPredictionForm((previous) => ({ ...previous, realAge: event.target.value }))} /></div><div className={styles.modalFooter}><button className={styles.actionBtn} onClick={closePredictionModal}>取消</button><button className={styles.primaryActionBtn} onClick={() => void createPrediction()} disabled={predictionSubmitting}><Upload size={15} />{predictionSubmitting ? '预测中...' : '开始预测'}</button></div></div><div><div className={styles.uploadPanel} onClick={() => predictionFileInputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); event.stopPropagation(); }} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); const file = event.dataTransfer.files?.[0]; if (file) loadPredictionFile(file); }}>{predictionPreview ? <img src={predictionPreview} alt="预测预览" className={styles.uploadPreviewImage} /> : <div className={styles.uploadPlaceholder}><Upload size={22} /><p>点击或拖拽上传影像文件</p><span>直接复用个人用户预测评估流程</span></div>}</div><input ref={predictionFileInputRef} type="file" accept="image/*" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) loadPredictionFile(file); }} /><div className={styles.selectionSummary}><p>个人用户：{selectedPatient ? `${selectedPatient.username} (UID: ${selectedPatient.id})` : '未选择'}</p><p>性别：{genderLabel(predictionForm.gender)}</p><p>文件：{predictionFile?.name || '未上传'}</p></div></div></div></div></div></div>}

      {selectedRecord && <div className={styles.modalOverlay}><div className={styles.modalContent}><div className={styles.modalHeader}><h3>预测详情 - #{selectedRecord.id.slice(-6)}</h3><button className={styles.closeBtn} onClick={() => setSelectedRecord(null)}><X size={20} /></button></div><div className={styles.modalBody}><div className={styles.detailGrid}><div><div className={styles.detailBlock}><h4>目标个人用户</h4><p>{selectedRecord.username || '未知用户'}{selectedRecord.user_id ? ` (UID: ${selectedRecord.user_id})` : ''}</p></div><div className={styles.detailBlock}><h4>预测骨龄</h4><p style={{ color: '#2563eb', fontSize: '1.5rem', fontWeight: 700 }}>{selectedRecord.predicted_age_years.toFixed(1)} 岁</p></div><div className={styles.detailBlock}><h4>性别</h4><p>{genderLabel(selectedRecord.gender)}</p></div>{selectedRecord.real_age_years != null && <div className={styles.detailBlock}><h4>实际年龄</h4><p>{selectedRecord.real_age_years.toFixed(1)} 岁</p></div>}{selectedRecord.predicted_adult_height != null && <div className={styles.detailBlock}><h4>预测成年身高</h4><p>{selectedRecord.predicted_adult_height.toFixed(1)} cm</p></div>}<div className={styles.detailBlock}><h4>异常特征</h4>{selectedRecord.anomalies && selectedRecord.anomalies.length > 0 ? <ul style={{ color: '#ef4444', margin: '0 0 1rem 0', paddingLeft: '1.2rem' }}>{selectedRecord.anomalies.map((anomaly, index) => <li key={`${anomaly.type}-${index}`}>{anomaly.type} ({(anomaly.score * 100).toFixed(0)}%)</li>)}</ul> : <p style={{ color: '#16a34a' }}>未发现明显异常特征。</p>}</div>{selectedRecord.rus_chn_details && <div className={styles.detailBlock}><h4>RUS-CHN 评分</h4><div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}><p style={{ margin: 0, fontWeight: 600 }}>总分：{selectedRecord.rus_chn_details.total_score ?? '暂无'}</p></div></div>}</div><div>{selectedRecord.heatmap_base64 ? <div style={{ textAlign: 'center' }}><h4 style={{ marginBottom: '0.5rem', color: '#64748b' }}>Grad-CAM 热力图</h4><div style={{ position: 'relative', display: 'inline-block' }}><img src={selectedRecord.heatmap_base64} alt="GradCAM" className={styles.detailImage} />{selectedRecord.anomalies?.map((item, index) => item.score > 0.45 ? <div key={`${item.type}-${index}`} style={{ left: `${(item.coord[0] - item.coord[2] / 2) * 100}%`, top: `${(item.coord[1] - item.coord[3] / 2) * 100}%`, width: `${item.coord[2] * 100}%`, height: `${item.coord[3] * 100}%`, position: 'absolute', border: '2px solid #ef4444', pointerEvents: 'none' }}><span className={styles.anomalyLabel}>{item.type}</span></div> : null)}</div></div> : <div className={styles.emptyDetailPanel}>暂无热力图数据。</div>}</div></div></div></div></div>}
    </div>
  );
}
