import { useEffect, useState } from 'react';
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
  User as UserIcon,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { API_BASE } from '../config';
import { useAuth, type AuthRole } from '../context/AuthContext';
import styles from './DoctorDashboard.module.css';

interface PredictionRecord {
  id: string;
  user_id: number;
  timestamp: number;
  filename: string;
  predicted_age_years: number;
  gender: string;
}

interface PredictionAnomaly {
  type: string;
  score: number;
  coord: number[];
}

interface PredictionDetail {
  id: string;
  predicted_age_years: number;
  gender: string;
  anomalies?: PredictionAnomaly[];
  heatmap_base64?: string;
  rus_chn_details?: {
    total_score?: number;
  };
}

interface QaItem {
  qid: number;
  owner: string;
  text: string;
  image: string;
  reply: string;
  createTime: string;
  updateTime: string;
}

interface ManagedAccount {
  id: number;
  username: string;
  role: AuthRole;
  created_at: string;
}

type ActiveTab = 'approvals' | 'articles' | 'qa' | 'ai' | 'accounts';
type ChatMessage = { role: 'user' | 'assistant'; text: string };

const roleLabelMap: Record<AuthRole, string> = {
  user: '个人用户',
  doctor: '临床医生',
  super_admin: '超级管理员',
};

const buildAuthHeaders = (json = false) => {
  const token = localStorage.getItem('boneage_token');
  const headers: Record<string, string> = {};
  if (json) headers['Content-Type'] = 'application/json';
  if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
};

const getBoxStyle = (coord: number[]) => {
  const [xc, yc, w, h] = coord;
  return {
    left: `${(xc - w / 2) * 100}%`,
    top: `${(yc - h / 2) * 100}%`,
    width: `${w * 100}%`,
    height: `${h * 100}%`,
    position: 'absolute' as const,
    border: '2px solid red',
    pointerEvents: 'none' as const,
  };
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
  const [records, setRecords] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<PredictionDetail | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('approvals');
  const [newArticle, setNewArticle] = useState({ title: '', content: '' });
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([]);
  const [qaList, setQaList] = useState<QaItem[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const [replyTexts, setReplyTexts] = useState<Record<number, string>>({});
  const [replySubmitting, setReplySubmitting] = useState<Record<number, boolean>>({});
  const [expandedQid, setExpandedQid] = useState<number | null>(null);
  const [accounts, setAccounts] = useState<ManagedAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountNotice, setAccountNotice] = useState<string | null>(null);
  const [accountMutationId, setAccountMutationId] = useState<number | null>(null);
  const [newAccount, setNewAccount] = useState({
    username: '',
    password: '',
    role: 'user' as AuthRole,
  });

  const superAdminCount = accounts.filter((item) => item.role === 'super_admin').length;

  useEffect(() => {
    void fetchRecords();
    void fetchDoctorQaList();
  }, []);

  useEffect(() => {
    if (isSuperAdmin && activeTab === 'accounts') {
      void fetchAccounts();
    } else if (activeTab === 'accounts') {
      setActiveTab('approvals');
    }
  }, [activeTab, isSuperAdmin]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/predictions`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setRecords(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDoctorQaList = async () => {
    setQaLoading(true);
    try {
      const response = await fetch(`${API_BASE}/qa/questions`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setQaList(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error('加载问答列表失败', error);
    } finally {
      setQaLoading(false);
    }
  };

  const fetchAccounts = async () => {
    if (!isSuperAdmin) return;
    setAccountsLoading(true);
    setAccountError(null);
    try {
      const response = await fetch(`${API_BASE}/auth/users`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setAccounts(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '加载账号列表失败');
    } finally {
      setAccountsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
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
      alert(error instanceof Error ? error.message : '回复失败');
    } finally {
      setReplySubmitting((previous) => ({ ...previous, [qid]: false }));
    }
  };

  const viewDetails = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/predictions/${id}`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = await response.json();
      setSelectedRecord(data.data as PredictionDetail);
    } catch (error) {
      alert(error instanceof Error ? error.message : '加载详情失败');
    }
  };

  const submitArticle = async () => {
    if (!newArticle.title.trim() || !newArticle.content.trim()) {
      alert('请填写完整的标题和内容');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/articles`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify(newArticle),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      alert('文章发布成功');
      setNewArticle({ title: '', content: '' });
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
            ? {
              predicted_age_years: selectedRecord.predicted_age_years,
              gender: selectedRecord.gender,
              anomalies: selectedRecord.anomalies,
            }
            : undefined,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : 'AI 助手请求失败');
      }
      setAiMessages((previous) => [...previous, { role: 'assistant', text: data.reply || '未返回内容' }]);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : '未知错误';
      setAiMessages((previous) => [...previous, { role: 'assistant', text: `调用失败：${messageText}` }]);
    } finally {
      setAiLoading(false);
    }
  };

  const createAccount = async () => {
    if (!newAccount.username.trim() || !newAccount.password.trim()) {
      setAccountError('用户名和密码不能为空');
      return;
    }
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
      setAccountNotice(`账号 ${newAccount.username} 创建成功`);
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
      setAccountNotice(`已将 ${account.username} 调整为${roleLabelMap[nextRole]}`);
      await fetchAccounts();
    } catch (error) {
      setAccountError(error instanceof Error ? error.message : '修改权限失败');
    } finally {
      setAccountMutationId(null);
    }
  };

  const deleteAccount = async (account: ManagedAccount) => {
    const confirmed = window.confirm(`确认删除账号 ${account.username} 吗？相关数据也会一并删除。`);
    if (!confirmed) return;
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
      setAccountNotice(`账号 ${account.username} 已删除`);
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.85rem', alignItems: 'end' }}>
          <div>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#475569', marginBottom: '0.35rem' }}>用户名</div>
            <input
              style={{ width: '100%', boxSizing: 'border-box', padding: '0.72rem', borderRadius: '10px', border: '1px solid #cbd5e1' }}
              placeholder="例如 doctor01"
              value={newAccount.username}
              onChange={(event) => setNewAccount((previous) => ({ ...previous, username: event.target.value }))}
            />
          </div>
          <div>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#475569', marginBottom: '0.35rem' }}>初始密码</div>
            <input
              type="password"
              style={{ width: '100%', boxSizing: 'border-box', padding: '0.72rem', borderRadius: '10px', border: '1px solid #cbd5e1' }}
              placeholder="至少 8 位，包含大小写字母和数字"
              value={newAccount.password}
              onChange={(event) => setNewAccount((previous) => ({ ...previous, password: event.target.value }))}
            />
          </div>
          <div>
            <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#475569', marginBottom: '0.35rem' }}>角色</div>
            <select
              style={{ width: '100%', boxSizing: 'border-box', padding: '0.72rem', borderRadius: '10px', border: '1px solid #cbd5e1', background: 'white' }}
              value={newAccount.role}
              onChange={(event) => setNewAccount((previous) => ({ ...previous, role: event.target.value as AuthRole }))}
            >
              {Object.entries(roleLabelMap).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <button
            className={styles.actionBtn}
            style={{ background: '#1d4ed8', color: 'white', border: 'none', justifyContent: 'center', minHeight: '44px' }}
            onClick={() => void createAccount()}
            disabled={accountsLoading}
          >
            <UserPlus size={16} />
            新建账号
          </button>
        </div>
        {(accountError || accountNotice) && (
          <div
            style={{
              marginTop: '1rem',
              borderRadius: '10px',
              padding: '0.75rem 0.9rem',
              border: `1px solid ${accountError ? '#fecaca' : '#bbf7d0'}`,
              background: accountError ? '#fff1f2' : '#f0fdf4',
              color: accountError ? '#b91c1c' : '#166534',
              fontSize: '0.88rem',
            }}
          >
            {accountError || accountNotice}
          </div>
        )}
      </div>

      <div className={styles.tableCard}>
        <div className={styles.cardHeader}>
          <h3>账号列表</h3>
          <button className={styles.refreshBtn} onClick={() => void fetchAccounts()} disabled={accountsLoading}>
            <RefreshCw size={16} className={accountsLoading ? 'spin' : ''} />
            刷新列表
          </button>
        </div>
        <div className={styles.tableWrapper}>
          <table>
            <thead>
              <tr>
                <th>用户名</th>
                <th>角色</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {accounts.length === 0 ? (
                <tr>
                  <td colSpan={4} className={styles.emptyState}>
                    {accountsLoading ? '正在加载账号列表...' : '暂无账号数据'}
                  </td>
                </tr>
              ) : (
                accounts.map((account) => {
                  const isSelf = account.username === username;
                  const isLastSuperAdmin = account.role === 'super_admin' && superAdminCount <= 1;
                  const disableMutation = accountMutationId === account.id;
                  const locked = isSelf || isLastSuperAdmin || disableMutation;
                  return (
                    <tr key={account.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          <span>{account.username}</span>
                          {isSelf && (
                            <span style={{ borderRadius: '999px', background: '#e0ecff', color: '#1d4ed8', fontSize: '0.72rem', padding: '0.12rem 0.45rem', fontWeight: 700 }}>
                              当前账号
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <select
                          value={account.role}
                          disabled={locked}
                          onChange={(event) => void updateAccountRole(account, event.target.value as AuthRole)}
                          style={{ padding: '0.45rem 0.55rem', borderRadius: '8px', border: '1px solid #cbd5e1', background: locked ? '#f8fafc' : '#fff' }}
                        >
                          {Object.entries(roleLabelMap).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{new Date(account.created_at).toLocaleString()}</td>
                      <td>
                        <button
                          className={styles.actionBtn}
                          style={{ color: '#b91c1c', borderColor: '#fecaca', opacity: locked ? 0.55 : 1 }}
                          onClick={() => void deleteAccount(account)}
                          disabled={locked}
                        >
                          <Trash2 size={14} />
                          删除
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  return (
    <div className={styles.dashboardLayout}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <Activity size={24} color="#3b82f6" />
          <span>{isSuperAdmin ? '超级管理员工作台' : '医生工作台'}</span>
        </div>

        <nav className={styles.sideNav}>
          <button className={`${styles.navItem} ${activeTab === 'approvals' ? styles.active : ''}`} onClick={() => setActiveTab('approvals')}>
            <Users size={18} />
            患者记录
          </button>
          <button className={`${styles.navItem} ${activeTab === 'articles' ? styles.active : ''}`} onClick={() => setActiveTab('articles')}>
            <FileText size={18} />
            健康科普
          </button>
          <button className={`${styles.navItem} ${activeTab === 'qa' ? styles.active : ''}`} onClick={() => setActiveTab('qa')}>
            <CheckCircle size={18} />
            问答回复
          </button>
          <button className={`${styles.navItem} ${activeTab === 'ai' ? styles.active : ''}`} onClick={() => setActiveTab('ai')}>
            <Bot size={18} />
            AI 助手
          </button>
          {isSuperAdmin && (
            <button className={`${styles.navItem} ${activeTab === 'accounts' ? styles.active : ''}`} onClick={() => setActiveTab('accounts')}>
              <ShieldCheck size={18} />
              账号管理
            </button>
          )}
        </nav>

        <div className={styles.userProfile}>
          <div className={styles.userInfo}>
            <UserIcon size={20} color="#cbd5e1" />
            <div>
              <span className={styles.username}>{username}</span>
              <span className={styles.roleBadge}>{displayRole}</span>
            </div>
          </div>
          <button onClick={handleLogout} className={styles.logoutBtn} title="退出登录">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className={styles.mainContent}>
        <header className={styles.topHeader}>
          <h2>{isSuperAdmin ? '超级管理员工作台' : '临床医生工作台'}</h2>
        </header>

        {activeTab === 'approvals' && (
          <div className={styles.workspaceGrid}>
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={`${styles.statIcon} ${styles.blue}`}><Users size={24} /></div>
                <div className={styles.statInfo}><h4>记录总数</h4><p>{records.length}</p></div>
              </div>
              <div className={styles.statCard}>
                <div className={`${styles.statIcon} ${styles.purple}`}><Activity size={24} /></div>
                <div className={styles.statInfo}><h4>当前可见</h4><p>{records.length}</p></div>
              </div>
              <div className={styles.statCard}>
                <div className={`${styles.statIcon} ${styles.green}`}><CheckCircle size={24} /></div>
                <div className={styles.statInfo}><h4>当前角色</h4><p style={{ fontSize: '1rem' }}>{displayRole}</p></div>
              </div>
            </div>

            <div className={styles.tableCard}>
              <div className={styles.cardHeader}>
                <h3>近期预测记录</h3>
                <button className={styles.refreshBtn} onClick={() => void fetchRecords()} disabled={loading}>
                  <RefreshCw size={16} className={loading ? 'spin' : ''} />
                  刷新列表
                </button>
              </div>
              <div className={styles.tableWrapper}>
                <table>
                  <thead>
                    <tr>
                      <th>记录 ID</th>
                      <th>日期时间</th>
                      <th>用户 ID</th>
                      <th>性别</th>
                      <th>预测年龄</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.length === 0 ? (
                      <tr><td colSpan={6} className={styles.emptyState}>{loading ? '正在加载记录...' : '暂无预测记录'}</td></tr>
                    ) : (
                      records.map((record) => (
                        <tr key={record.id}>
                          <td style={{ fontFamily: 'monospace', color: '#64748b' }}>#{record.id.slice(0, 8)}</td>
                          <td>{new Date(record.timestamp).toLocaleString()}</td>
                          <td>UID: {record.user_id}</td>
                          <td><span className={`${styles.genderTag} ${record.gender === 'male' ? styles.male : styles.female}`}>{record.gender === 'male' ? '男' : '女'}</span></td>
                          <td style={{ fontWeight: 600 }}>{record.predicted_age_years.toFixed(1)} 岁</td>
                          <td><button className={styles.actionBtn} onClick={() => void viewDetails(record.id)}><Eye size={14} />查看详情</button></td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'articles' && (
          <div className={styles.workspaceGrid}>
            <div className={styles.tableCard} style={{ padding: '2rem' }}>
              <h3 style={{ margin: '0 0 1.5rem 0' }}>发布科普文章</h3>
              <input
                style={{ width: '100%', boxSizing: 'border-box', padding: '0.8rem', marginBottom: '1rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '1rem' }}
                placeholder="文章标题"
                value={newArticle.title}
                onChange={(event) => setNewArticle((previous) => ({ ...previous, title: event.target.value }))}
              />
              <textarea
                style={{ width: '100%', boxSizing: 'border-box', padding: '0.8rem', marginBottom: '1rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '1rem', minHeight: '200px', resize: 'vertical' }}
                placeholder="在这里编写文章内容..."
                value={newArticle.content}
                onChange={(event) => setNewArticle((previous) => ({ ...previous, content: event.target.value }))}
              />
              <button className={styles.actionBtn} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '0.8rem 2rem', fontSize: '1rem' }} onClick={() => void submitArticle()}>
                发布文章
              </button>
            </div>
          </div>
        )}

        {activeTab === 'qa' && (
          <div style={{ padding: '0 0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>患者问答</h3>
              <button
                onClick={() => void fetchDoctorQaList()}
                disabled={qaLoading}
                style={{ border: '1px solid #cad7f0', background: 'white', color: '#274374', borderRadius: '8px', padding: '0.35rem 0.85rem', fontWeight: 700, cursor: 'pointer' }}
              >
                {qaLoading ? '刷新中...' : '刷新列表'}
              </button>
            </div>
            {qaList.length === 0 && !qaLoading && (
              <p style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem 0' }}>暂无患者提问。</p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {qaList.map((question) => (
                <div key={question.qid} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white', overflow: 'hidden' }}>
                  <div
                    style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer', background: expandedQid === question.qid ? '#f0f7ff' : 'white' }}
                    onClick={() => setExpandedQid(expandedQid === question.qid ? null : question.qid)}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>
                        患者：<strong>{question.owner}</strong> · {new Date(question.createTime).toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.92rem', color: '#1e293b', lineHeight: 1.4 }}>{question.text}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      {question.reply ? (
                        <span style={{ background: '#dcfce7', color: '#15803d', fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '999px' }}>已回复</span>
                      ) : (
                        <span style={{ background: '#fef9c3', color: '#92400e', fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '999px' }}>待回复</span>
                      )}
                    </div>
                  </div>
                  {expandedQid === question.qid && (
                    <div style={{ borderTop: '1px solid #e2e8f0', padding: '1rem' }}>
                      {question.image && (
                        <div style={{ marginBottom: '0.85rem' }}>
                          <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '0.35rem' }}>附带图片：</div>
                          <img src={question.image} alt="患者附图" style={{ maxWidth: '280px', maxHeight: '200px', objectFit: 'contain', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                        </div>
                      )}
                      {question.reply && (
                        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '0.7rem 0.85rem', marginBottom: '0.85rem', fontSize: '0.9rem', color: '#14532d', lineHeight: 1.5 }}>
                          <strong>已有回复：</strong> {question.reply}
                        </div>
                      )}
                      <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.4rem', fontWeight: 600 }}>
                        {question.reply ? '修改回复' : '填写回复'}
                      </div>
                      <textarea
                        placeholder="请输入专业回复内容..."
                        value={replyTexts[question.qid] || ''}
                        onChange={(event) => setReplyTexts((previous) => ({ ...previous, [question.qid]: event.target.value }))}
                        style={{ width: '100%', minHeight: '90px', borderRadius: '9px', border: '1px solid #cbd5e1', padding: '0.65rem', fontSize: '0.9rem', resize: 'vertical', boxSizing: 'border-box', fontFamily: 'inherit' }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}>
                        <button
                          onClick={() => void replyToQuestion(question.qid)}
                          disabled={replySubmitting[question.qid] || !replyTexts[question.qid]?.trim()}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: 'linear-gradient(140deg,#1d4ed8,#173c9c)', color: '#fff', border: 'none', borderRadius: '9px', padding: '0.5rem 1.2rem', fontWeight: 700, cursor: 'pointer', fontSize: '0.9rem', opacity: (!replyTexts[question.qid]?.trim() || replySubmitting[question.qid]) ? 0.6 : 1 }}
                        >
                          {replySubmitting[question.qid] ? '提交中...' : question.reply ? '更新回复' : '提交回复'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className={styles.workspaceGrid}>
            <div className={styles.tableCard} style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 1rem 0' }}>AI 临床助手</h3>
              <p style={{ margin: '0 0 1rem 0', color: '#64748b' }}>
                可输入病例分析需求、阅片疑问或后续检查建议，由 AI 提供结构化辅助意见。
              </p>
              <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, minHeight: 280, maxHeight: 380, overflow: 'auto', padding: '0.75rem', background: '#f8fafc' }}>
                {aiMessages.length === 0 && <p style={{ color: '#64748b', margin: 0 }}>暂无对话，请先输入问题。</p>}
                {aiMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    style={{
                      marginBottom: '0.6rem',
                      padding: '0.6rem 0.7rem',
                      borderRadius: 10,
                      background: message.role === 'user' ? '#dbeafe' : 'white',
                      border: '1px solid #e2e8f0',
                    }}
                  >
                    <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.2rem' }}>{message.role === 'user' ? '你' : 'AI 助手'}</div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{message.text}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.6rem', marginTop: '0.8rem' }}>
                <textarea
                  placeholder="例如：请根据当前预测结果给出鉴别诊断建议。"
                  value={aiInput}
                  onChange={(event) => setAiInput(event.target.value)}
                  style={{ width: '100%', minHeight: 90, borderRadius: 10, border: '1px solid #cbd5e1', padding: '0.7rem', resize: 'vertical' }}
                />
                <button
                  className={styles.actionBtn}
                  style={{ alignSelf: 'end', height: 42, background: '#3b82f6', color: '#fff', border: 'none' }}
                  onClick={() => void askAiAssistant()}
                  disabled={aiLoading}
                >
                  <Send size={14} />
                  {aiLoading ? '运行中...' : '发送'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'accounts' && isSuperAdmin && renderAccountsTab()}
      </main>

      {selectedRecord && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h3>预测详情 - #{selectedRecord.id.slice(-6)}</h3>
              <button className={styles.closeBtn} onClick={() => setSelectedRecord(null)}>
                <X size={20} />
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.detailGrid}>
                <div>
                  <div className={styles.detailBlock}>
                    <h4>预测骨龄</h4>
                    <p style={{ color: '#2563eb', fontSize: '1.5rem', fontWeight: 700 }}>
                      {selectedRecord.predicted_age_years.toFixed(1)} 岁
                    </p>
                  </div>
                  <div className={styles.detailBlock}>
                    <h4>性别</h4>
                    <p>{selectedRecord.gender === 'male' ? '男' : '女'}</p>
                  </div>
                  <div className={styles.detailBlock}>
                    <h4>异常特征</h4>
                    {selectedRecord.anomalies && selectedRecord.anomalies.length > 0 ? (
                      <ul style={{ color: '#ef4444', margin: '0 0 1rem 0', paddingLeft: '1.2rem' }}>
                        {selectedRecord.anomalies.map((anomaly, index) => (
                          <li key={`${anomaly.type}-${index}`}>
                            {anomaly.type} ({(anomaly.score * 100).toFixed(0)}%)
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ color: '#16a34a' }}>未发现明显异常特征。</p>
                    )}
                  </div>
                  {selectedRecord.rus_chn_details && (
                    <div className={styles.detailBlock}>
                      <h4>RUS-CHN 评分</h4>
                      <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                        <p style={{ margin: 0, fontWeight: 600 }}>
                          总分：{selectedRecord.rus_chn_details.total_score ?? '暂无'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                <div>
                  {selectedRecord.heatmap_base64 && (
                    <div style={{ textAlign: 'center' }}>
                      <h4 style={{ marginBottom: '0.5rem', color: '#64748b' }}>Grad-CAM 热力图</h4>
                      <div style={{ position: 'relative', display: 'inline-block' }}>
                        <img src={selectedRecord.heatmap_base64} alt="GradCAM" className={styles.detailImage} />
                        {selectedRecord.anomalies?.map((item, index) => (
                          item.score > 0.45 ? (
                            <div key={`${item.type}-${index}`} style={getBoxStyle(item.coord)}>
                              <span style={{ position: 'absolute', top: -16, left: 0, background: 'red', color: 'white', fontSize: 10, padding: 2 }}>
                                {item.type}
                              </span>
                            </div>
                          ) : null
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
