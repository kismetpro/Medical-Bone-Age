import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Activity, Users, FileText, CheckCircle, LogOut, User as UserIcon, RefreshCw, Eye, X, Bot, Send } from 'lucide-react';
import styles from './DoctorDashboard.module.css';

import { API_BASE } from '../config';


interface PredictionRecord {
    id: string;
    user_id: number;
    timestamp: number;
    filename: string;
    predicted_age_years: number;
    gender: string;
}

export default function DoctorDashboard() {
    const { username, logout } = useAuth();
    const navigate = useNavigate();
    const [records, setRecords] = useState<PredictionRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
    const [activeTab, setActiveTab] = useState<'approvals' | 'articles' | 'qa' | 'ai'>('approvals');
    const [newArticle, setNewArticle] = useState({ title: '', content: '' });
    const [aiInput, setAiInput] = useState('');
    const [aiLoading, setAiLoading] = useState(false);
    const [aiMessages, setAiMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
    // --- QA Forum state ---
    const [qaList, setQaList] = useState<any[]>([]);
    const [qaLoading, setQaLoading] = useState(false);
    const [replyTexts, setReplyTexts] = useState<Record<number, string>>({});
    const [replySubmitting, setReplySubmitting] = useState<Record<number, boolean>>({});
    const [expandedQid, setExpandedQid] = useState<number | null>(null);
    const buildAuthHeaders = (json = false) => {
        const token = localStorage.getItem('boneage_token');
        const headers: Record<string, string> = {};
        if (json) headers['Content-Type'] = 'application/json';
        if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) {
            headers['Authorization'] = `Bearer ${token}`;
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
            pointerEvents: 'none' as const
        };
    };

    const fetchRecords = async () => {
        setLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/predictions`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setRecords(data.items);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRecords();
        fetchDoctorQaList();
    }, []);

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const fetchDoctorQaList = async () => {
        setQaLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/qa/questions`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setQaList(data.items || []);
            }
        } catch (e) { console.error('获取问答失败', e); }
        finally { setQaLoading(false); }
    };

    const replyToQuestion = async (qid: number) => {
        const reply = replyTexts[qid]?.trim();
        if (!reply) return;
        setReplySubmitting(prev => ({ ...prev, [qid]: true }));
        try {
            const resp = await fetch(`${API_BASE}/qa/questions/${qid}/reply`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ reply })
            });
            if (resp.ok) {
                setReplyTexts(prev => ({ ...prev, [qid]: '' }));
                await fetchDoctorQaList();
            } else {
                const data = await resp.json().catch(() => ({}));
                alert(data.detail || '回复失败');
            }
        } catch (e) { alert('回复失败'); }
        finally { setReplySubmitting(prev => ({ ...prev, [qid]: false })); }
    };

    const viewDetails = async (id: string) => {
        try {
            const resp = await fetch(`${API_BASE}/predictions/${id}`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setSelectedRecord(data.data);
            }
        } catch (e) {
            alert('加载详情失败');
        }
    };

    const submitArticle = async () => {
        if (!newArticle.title || !newArticle.content) return alert('请填写完所有字段');
        try {
            const resp = await fetch(`${API_BASE}/articles`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify(newArticle)
            });
            if (resp.ok) {
                alert('文章发布成功！');
                setNewArticle({ title: '', content: '' });
            } else alert('发布失败');
        } catch (e) {
            alert('发布出错');
        }
    };

    const askAiAssistant = async () => {
        const msg = aiInput.trim();
        if (!msg) return;
        setAiLoading(true);
        setAiMessages(prev => [...prev, { role: 'user', text: msg }]);
        setAiInput('');
        try {
            const resp = await fetch(`${API_BASE}/doctor/ai-assistant`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({
                    message: msg,
                    prediction_id: selectedRecord?.id || undefined,
                    context: selectedRecord ? {
                        predicted_age_years: selectedRecord.predicted_age_years,
                        gender: selectedRecord.gender,
                        anomalies: selectedRecord.anomalies
                    } : undefined
                })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || 'AI 助手调用失败');
            setAiMessages(prev => [...prev, { role: 'assistant', text: data.reply || '未返回内容' }]);
        } catch (e: any) {
            setAiMessages(prev => [...prev, { role: 'assistant', text: `调用失败：${e.message || '未知错误'}` }]);
        } finally {
            setAiLoading(false);
        }
    };

    return (
        <div className={styles.dashboardLayout}>
            <aside className={styles.sidebar}>
                <div className={styles.brand}>
                    <Activity size={24} color="#3b82f6" />
                    <span>医生工作台</span>
                </div>

                <nav className={styles.sideNav}>
                    <button className={`${styles.navItem} ${activeTab === 'approvals' ? styles.active : ''}`} onClick={() => setActiveTab('approvals')}><Users size={18} /> 患者记录审批</button>
                    <button className={`${styles.navItem} ${activeTab === 'articles' ? styles.active : ''}`} onClick={() => setActiveTab('articles')}><FileText size={18} /> 发布健康科普</button>
                    <button className={`${styles.navItem} ${activeTab === 'qa' ? styles.active : ''}`} onClick={() => setActiveTab('qa')}><CheckCircle size={18} /> 问答论坛回复</button>
                    <button className={`${styles.navItem} ${activeTab === 'ai' ? styles.active : ''}`} onClick={() => setActiveTab('ai')}><Bot size={18} /> AI 辅助诊断</button>
                </nav>

                <div className={styles.userProfile}>
                    <div className={styles.userInfo}>
                        <UserIcon size={20} color="#cbd5e1" />
                        <div>
                            <span className={styles.username}>医生 {username}</span>
                            <span className={styles.roleBadge}>管理员</span>
                        </div>
                    </div>
                    <button onClick={handleLogout} className={styles.logoutBtn} title="退出登录">
                        <LogOut size={16} />
                    </button>
                </div>
            </aside>

            <main className={styles.mainContent}>
                <header className={styles.topHeader}>
                    <h2>临床工作流与仪表盘</h2>
                </header>

                {activeTab === 'approvals' && (
                    <div className={styles.workspaceGrid}>
                        {/* Stats */}
                        <div className={styles.statsGrid}>
                            <div className={styles.statCard}>
                                <div className={`${styles.statIcon} ${styles.blue}`}><Users size={24} /></div>
                                <div className={styles.statInfo}>
                                    <h4>评估总数</h4>
                                    <p>{records.length}</p>
                                </div>
                            </div>
                            <div className={styles.statCard}>
                                <div className={`${styles.statIcon} ${styles.purple}`}><Activity size={24} /></div>
                                <div className={styles.statInfo}>
                                    <h4>待复核记录</h4>
                                    <p>{records.length}</p>
                                </div>
                            </div>
                            <div className={styles.statCard}>
                                <div className={`${styles.statIcon} ${styles.green}`}><CheckCircle size={24} /></div>
                                <div className={styles.statInfo}>
                                    <h4>已批准报告</h4>
                                    <p>0</p>
                                </div>
                            </div>
                        </div>

                        {/* Table */}
                        <div className={styles.tableCard}>
                            <div className={styles.cardHeader}>
                                <h3>近期患者评估</h3>
                                <button className={styles.refreshBtn} onClick={fetchRecords} disabled={loading}>
                                    <RefreshCw size={16} className={loading ? 'spin' : ''} /> 刷新列表
                                </button>
                            </div>
                            <div className={styles.tableWrapper}>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>记录 ID</th>
                                            <th>日期与时间</th>
                                            <th>用户 ID</th>
                                            <th>性别</th>
                                            <th>预测年龄</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {records.length === 0 ? (
                                            <tr><td colSpan={6} className={styles.emptyState}>数据库中未找到预测记录。</td></tr>
                                        ) : (
                                            records.map(record => (
                                                <tr key={record.id}>
                                                    <td style={{ fontFamily: 'monospace', color: '#64748b' }}>#{record.id.slice(0, 8)}</td>
                                                    <td>{new Date(record.timestamp).toLocaleString()}</td>
                                                    <td>UID: {record.user_id}</td>
                                                    <td>
                                                        <span className={`${styles.genderTag} ${record.gender === 'male' ? styles.male : styles.female}`}>
                                                            {record.gender === 'male' ? '男' : '女'}
                                                        </span>
                                                    </td>
                                                    <td style={{ fontWeight: 600 }}>{record.predicted_age_years.toFixed(1)} 岁</td>
                                                    <td>
                                                        <button className={styles.actionBtn} onClick={() => viewDetails(record.id)}>
                                                            <Eye size={14} /> 查看 AI 识别结果
                                                        </button>
                                                    </td>
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
                            <h3 style={{ marginBottom: '1.5rem', marginTop: 0 }}>编写新健康科普文章</h3>
                            <input
                                style={{ width: '100%', boxSizing: 'border-box', padding: '0.8rem', marginBottom: '1rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '1rem' }}
                                placeholder="文章标题（例如：儿童生长发育建议）"
                                value={newArticle.title}
                                onChange={e => setNewArticle({ ...newArticle, title: e.target.value })}
                            />
                            <textarea
                                style={{ width: '100%', boxSizing: 'border-box', padding: '0.8rem', marginBottom: '1rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '1rem', minHeight: '200px', resize: 'vertical' }}
                                placeholder="在此处编写文章正文..."
                                value={newArticle.content}
                                onChange={e => setNewArticle({ ...newArticle, content: e.target.value })}
                            />
                            <button className={styles.actionBtn} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '0.8rem 2rem', fontSize: '1rem' }} onClick={submitArticle}>
                                发布文章
                            </button>
                        </div>
                    </div>
                )}

                {activeTab === 'qa' && (
                    <div style={{ padding: '0 0.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h3 style={{ margin: 0 }}>患者问答论坛回复</h3>
                            <button
                                onClick={fetchDoctorQaList}
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
                            {qaList.map(q => (
                                <div key={q.qid} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white', overflow: 'hidden' }}>
                                    {/* 问题头部 */}
                                    <div
                                        style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer', background: expandedQid === q.qid ? '#f0f7ff' : 'white' }}
                                        onClick={() => setExpandedQid(expandedQid === q.qid ? null : q.qid)}
                                    >
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>
                                                患者：<strong>{q.owner}</strong> &nbsp;•&nbsp; {new Date(q.createTime).toLocaleString()}
                                            </div>
                                            <div style={{ fontSize: '0.92rem', color: '#1e293b', lineHeight: 1.4 }}>{q.text}</div>
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                            {q.reply ? (
                                                <span style={{ background: '#dcfce7', color: '#15803d', fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '999px' }}>已回复</span>
                                            ) : (
                                                <span style={{ background: '#fef9c3', color: '#92400e', fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '999px' }}>待回复</span>
                                            )}
                                            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{expandedQid === q.qid ? '▲' : '▼'}</span>
                                        </div>
                                    </div>

                                    {/* 展开内容 */}
                                    {expandedQid === q.qid && (
                                        <div style={{ borderTop: '1px solid #e2e8f0', padding: '1rem' }}>
                                            {/* 附图 */}
                                            {q.image && (
                                                <div style={{ marginBottom: '0.85rem' }}>
                                                    <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '0.35rem' }}>患者附图：</div>
                                                    <img src={q.image} alt="患者附件" style={{ maxWidth: '280px', maxHeight: '200px', objectFit: 'contain', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                                                </div>
                                            )}
                                            {/* 已有回复 */}
                                            {q.reply && (
                                                <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '0.7rem 0.85rem', marginBottom: '0.85rem', fontSize: '0.9rem', color: '#14532d', lineHeight: 1.5 }}>
                                                    <strong>已有回复：</strong>{q.reply}
                                                </div>
                                            )}
                                            {/* 回复输入框 */}
                                            <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '0.4rem', fontWeight: 600 }}>
                                                {q.reply ? '修改回复' : '输入回复'}
                                            </div>
                                            <textarea
                                                placeholder="在此输入专业医学建议..."
                                                value={replyTexts[q.qid] || ''}
                                                onChange={e => setReplyTexts(prev => ({ ...prev, [q.qid]: e.target.value }))}
                                                style={{ width: '100%', minHeight: '90px', borderRadius: '9px', border: '1px solid #cbd5e1', padding: '0.65rem', fontSize: '0.9rem', resize: 'vertical', boxSizing: 'border-box', fontFamily: 'inherit' }}
                                            />
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}>
                                                <button
                                                    onClick={() => replyToQuestion(q.qid)}
                                                    disabled={replySubmitting[q.qid] || !replyTexts[q.qid]?.trim()}
                                                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: 'linear-gradient(140deg,#1d4ed8,#173c9c)', color: '#fff', border: 'none', borderRadius: '9px', padding: '0.5rem 1.2rem', fontWeight: 700, cursor: 'pointer', fontSize: '0.9rem', opacity: (!replyTexts[q.qid]?.trim() || replySubmitting[q.qid]) ? 0.6 : 1 }}
                                                >
                                                    {replySubmitting[q.qid] ? '提交中...' : (q.reply ? '更新回复' : '提交回复')}
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
                            <h3 style={{ margin: '0 0 1rem 0' }}>DeepSeek AI 辅助诊断</h3>
                            <p style={{ margin: '0 0 1rem 0', color: '#64748b' }}>
                                可输入病例描述、读片疑问或让 AI 根据当前已查看的记录给出结构化建议。
                            </p>
                            <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, minHeight: 280, maxHeight: 380, overflow: 'auto', padding: '0.75rem', background: '#f8fafc' }}>
                                {aiMessages.length === 0 && <p style={{ color: '#64748b', margin: 0 }}>暂无对话，先输入一个问题。</p>}
                                {aiMessages.map((m, idx) => (
                                    <div key={idx} style={{
                                        marginBottom: '0.6rem',
                                        padding: '0.6rem 0.7rem',
                                        borderRadius: 10,
                                        background: m.role === 'user' ? '#dbeafe' : 'white',
                                        border: '1px solid #e2e8f0'
                                    }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.2rem' }}>{m.role === 'user' ? '你' : 'AI 医助'}</div>
                                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{m.text}</div>
                                    </div>
                                ))}
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.6rem', marginTop: '0.8rem' }}>
                                <textarea
                                    placeholder="例如：请根据此患儿骨龄结果给出鉴别诊断建议和下一步检查方案。"
                                    value={aiInput}
                                    onChange={(e) => setAiInput(e.target.value)}
                                    style={{ width: '100%', minHeight: 90, borderRadius: 10, border: '1px solid #cbd5e1', padding: '0.7rem', resize: 'vertical' }}
                                />
                                <button
                                    className={styles.actionBtn}
                                    style={{ alignSelf: 'end', height: 42, background: '#3b82f6', color: '#fff', border: 'none' }}
                                    onClick={askAiAssistant}
                                    disabled={aiLoading}
                                >
                                    <Send size={14} /> {aiLoading ? '分析中...' : '发送'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Review Modal */}
            {selectedRecord && (
                <div className={styles.modalOverlay}>
                    <div className={styles.modalContent}>
                        <div className={styles.modalHeader}>
                            <h3>AI 评估与审阅 - #{selectedRecord.id.slice(-6)}</h3>
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
                                        <h4>性别参数</h4>
                                        <p>{selectedRecord.gender === 'male' ? '男' : '女'}</p>
                                    </div>
                                    <div className={styles.detailBlock}>
                                        <h4>检出异常特征</h4>
                                        {selectedRecord.anomalies && selectedRecord.anomalies.length > 0 ? (
                                            <ul style={{ color: '#ef4444', margin: '0 0 1rem 0', paddingLeft: '1.2rem' }}>
                                                {selectedRecord.anomalies.map((a: any, i: number) => (
                                                    <li key={i}>{a.type} (置信度 {(a.score * 100).toFixed(0)}%)</li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p style={{ color: '#16a34a' }}>未检测到明显的异常（如骨折/异物）</p>
                                        )}
                                    </div>
                                    {selectedRecord.rus_chn_details && (
                                        <div className={styles.detailBlock}>
                                            <h4>RUS-CHN 计分计算</h4>
                                            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                                                <p style={{ margin: 0, fontWeight: 600 }}>骨成熟度总分：{selectedRecord.rus_chn_details.total_score}</p>
                                                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                                                    此总分计算得出的发育对应靶骨龄为预测结果
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <div>
                                    {selectedRecord.heatmap_base64 && (
                                        <div style={{ textAlign: 'center' }}>
                                            <h4 style={{ marginBottom: '0.5rem', color: '#64748b' }}>Grad-CAM 可视化核验图</h4>
                                            <div style={{ position: 'relative', display: 'inline-block' }}>
                                                <img src={selectedRecord.heatmap_base64} alt="GradCAM" className={styles.detailImage} />
                                                {selectedRecord.anomalies?.map((item: any, idx: number) => (
                                                    item.score > 0.45 && (
                                                        <div key={idx} style={getBoxStyle(item.coord)}>
                                                            <span style={{ position: 'absolute', top: -16, left: 0, background: 'red', color: 'white', fontSize: 10, padding: 2 }}>{item.type}</span>
                                                        </div>
                                                    )
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
