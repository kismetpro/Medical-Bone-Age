import React, { useState, useEffect, useRef } from 'react';
import { FileSpreadsheet, MessageCircle, Upload, Plus, Trash2, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { buildAuthHeaders, readErrorMessage } from '../lib/api';
import { API_BASE } from '../config';
import userStyles from './UserDashboard/UserDashboard.module.css';

const CommunityPage: React.FC = () => {
    const { role, username } = useAuth();
    const isDoctor = role === 'doctor' || role === 'super_admin';

    // 科普文章状态
    const [articles, setArticles] = useState<any[]>([]);
    const [newArticle, setNewArticle] = useState({ title: '', content: '' });

    // 问答列表状态
    const [qaList, setQaList] = useState<any[]>([]);
    const [qaLoading, setQaLoading] = useState(false);
    const [qaText, setQaText] = useState('');
    const [qaSubmitting, setQaSubmitting] = useState(false);
    const [qaImageBase64, setQaImageBase64] = useState<string | null>(null);
    const [expandedQid, setExpandedQid] = useState<number | null>(null);
    const [replyTexts, setReplyTexts] = useState<Record<number, string>>({});
    const [replySubmitting, setReplySubmitting] = useState<Record<number, boolean>>({});

    const qaImageInputRef = useRef<HTMLInputElement | null>(null);

    const fetchArticles = async () => {
        try {
            const resp = await fetch(`${API_BASE}/articles`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setArticles(data.items || []);
            }
        } catch (e) { console.error('获取文章失败'); }
    };

    const fetchQaList = async () => {
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
        } catch (e) { console.error('获取问答列表失败', e); }
        finally { setQaLoading(false); }
    };

    const submitQuestion = async () => {
        if (!qaText.trim()) return;
        if (!qaImageBase64) return;
        setQaSubmitting(true);
        try {
            const resp = await fetch(`${API_BASE}/qa/questions`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ text: qaText.trim(), image: qaImageBase64 })
            });
            if (!resp.ok) throw new Error('提问失败');
            setQaText('');
            setQaImageBase64(null);
            await fetchQaList();
        } catch (e: any) { alert(e.message); }
        finally { setQaSubmitting(false); }
    };

    const deleteQuestion = async (qid: number) => {
        if (!window.confirm('确认删除该提问吗？')) return;
        try {
            const resp = await fetch(`${API_BASE}/qa/questions/${qid}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) await fetchQaList();
        } catch (e) { alert('删除失败'); }
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
            if (!resp.ok) throw new Error(await readErrorMessage(resp));
            setReplyTexts(prev => ({ ...prev, [qid]: '' }));
            await fetchQaList();
        } catch (e: any) { alert(e.message); }
        finally { setReplySubmitting(prev => ({ ...prev, [qid]: false })); }
    };

    const submitArticle = async () => {
        if (!newArticle.title.trim() || !newArticle.content.trim()) return alert('请填写完整。');
        try {
            const resp = await fetch(`${API_BASE}/articles`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify(newArticle)
            });
            if (!resp.ok) throw new Error('发布失败');
            setNewArticle({ title: '', content: '' });
            alert('发布成功');
            await fetchArticles();
        } catch (e: any) { alert(e.message); }
    };

    useEffect(() => {
        fetchArticles();
        fetchQaList();
    }, []);

    const handleQaImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = (ev) => setQaImageBase64(ev.target?.result as string);
        reader.readAsDataURL(f);
    };

    return (
        <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            
            {/* 专家科普区 */}
            <div className={userStyles.communityPanel}>
                <div className={userStyles.communityPanelHeader}>
                    <FileSpreadsheet size={20} color="#3b82f6" />
                    <h3 style={{ margin: '0 0 0 0.5rem' }}>专家健康科普</h3>
                    {isDoctor && <span className={userStyles.aiTag}>文章发布</span>}
                </div>
                
                {isDoctor && (
                    <div style={{ marginBottom: '1.5rem', padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '12px', background: '#f8fafc' }}>
                        <h4 style={{ margin: '0 0 1rem 0' }}>发布新科普文章</h4>
                        <input 
                            style={{ width: '100%', padding: '0.6rem', marginBottom: '0.6rem', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                            placeholder="文章标题"
                            value={newArticle.title}
                            onChange={e => setNewArticle(prev => ({ ...prev, title: e.target.value }))}
                        />
                        <textarea 
                            style={{ width: '100%', padding: '0.6rem', marginBottom: '0.6rem', borderRadius: '8px', border: '1px solid #cbd5e1', minHeight: '100px' }}
                            placeholder="文章内容..."
                            value={newArticle.content}
                            onChange={e => setNewArticle(prev => ({ ...prev, content: e.target.value }))}
                        />
                        <button 
                            style={{ width: '100%', padding: '0.6rem', color: '#fff', background: '#3b82f6', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}
                            onClick={submitArticle}
                        >
                            发布文章
                        </button>
                    </div>
                )}

                {articles.length === 0 ? (
                    <p className={userStyles.communityEmpty}>目前暂无科普文章。</p>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
                        {articles.map(article => (
                            <div key={article.id} className={userStyles.articleCard}>
                                <h4 className={userStyles.articleTitle}>{article.title}</h4>
                                <p className={userStyles.articleMeta}>发布者：{article.author_name} 医生 • {new Date(article.created_at).toLocaleDateString()}</p>
                                <p className={userStyles.articleContent}>{article.content}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* 问答论坛区 */}
            <div className={userStyles.communityPanel}>
                <div className={userStyles.communityPanelHeader}>
                    <MessageCircle size={20} color="#3b82f6" />
                    <h3 style={{ margin: '0 0 0 0.5rem' }}>问答论坛</h3>
                    <button className={userStyles.refreshSmallBtn} onClick={fetchQaList} disabled={qaLoading} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <RefreshCw size={14} className={qaLoading ? 'spin' : ''} /> 刷新
                    </button>
                </div>

                {!isDoctor && (
                    <div className={userStyles.qaForm} style={{ marginBottom: '1.5rem' }}>
                        <p className={userStyles.communityDesc}>提出骨龄发育相关疑问，医生将为您解答。</p>
                        <textarea
                            className={userStyles.qaTextarea}
                            placeholder="描述您的问题..."
                            value={qaText}
                            onChange={e => setQaText(e.target.value)}
                            rows={3}
                        />
                        <div className={userStyles.qaFormActions}>
                            <div className={userStyles.qaImageSelect}>
                                <input type="file" accept="image/*" style={{ display: 'none' }} ref={qaImageInputRef} onChange={handleQaImageSelect} />
                                <button className={userStyles.qaImageBtn} onClick={() => qaImageInputRef.current?.click()}>
                                    <Upload size={14} /> {qaImageBase64 ? '已选择影像' : '附上影像附件'}
                                </button>
                                {qaImageBase64 && <img src={qaImageBase64} alt="预览" className={userStyles.qaImageThumb} />}
                            </div>
                            <button className={userStyles.qaSubmitBtn} onClick={submitQuestion} disabled={qaSubmitting || !qaText.trim() || !qaImageBase64}>
                                <Plus size={14} /> {qaSubmitting ? '提交中...' : '提交问题'}
                            </button>
                        </div>
                    </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {qaList.length === 0 && !qaLoading && <p className={userStyles.communityEmpty}>暂无问答记录。</p>}
                    {qaList.map(q => (
                        <div key={q.qid} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white', overflow: 'hidden' }}>
                            <div 
                                style={{ padding: '1rem', cursor: 'pointer', background: expandedQid === q.qid ? '#f0f7ff' : 'white' }}
                                onClick={() => setExpandedQid(expandedQid === q.qid ? null : q.qid)}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                    <span style={{ fontSize: '0.8rem', color: '#64748b' }}>用户：<strong>{q.owner}</strong> · {new Date(q.createTime).toLocaleString()}</span>
                                    <span style={{ 
                                        padding: '0.2rem 0.5rem', borderRadius: '999px', fontSize: '0.7rem', fontWeight: 'bold',
                                        background: q.reply ? '#dcfce7' : '#fef3c7', color: q.reply ? '#15803d' : '#92400e'
                                    }}>{q.reply ? '已回复' : '待回复'}</span>
                                </div>
                                <div style={{ fontSize: '0.95rem', fontWeight: 500 }}>{q.text}</div>
                            </div>
                            
                            {expandedQid === q.qid && (
                                <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0' }}>
                                    {q.image && <img src={q.image} alt="附件" style={{ maxWidth: '300px', borderRadius: '8px', marginBottom: '1rem' }} />}
                                    {q.reply && (
                                        <div style={{ padding: '1rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', marginBottom: '1rem' }}>
                                            <strong style={{ color: '#15803d' }}>医生回复：</strong> {q.reply}
                                        </div>
                                    )}
                                    
                                    {isDoctor && (
                                        <div>
                                            <textarea 
                                                style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', minHeight: '90px' }}
                                                placeholder="输入专业回复..."
                                                value={replyTexts[q.qid] || ''}
                                                onChange={e => setReplyTexts(prev => ({ ...prev, [q.qid]: e.target.value }))}
                                            />
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem', gap: '0.5rem' }}>
                                                {q.owner === username && (
                                                    <button onClick={() => deleteQuestion(q.qid)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>删除</button>
                                                )}
                                                <button 
                                                    style={{ padding: '0.5rem 1rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold' }}
                                                    onClick={() => replyToQuestion(q.qid)}
                                                    disabled={replySubmitting[q.qid] || !replyTexts[q.qid]?.trim()}
                                                >
                                                    {replySubmitting[q.qid] ? '提交中...' : (q.reply ? '修改回复' : '提交回复')}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    
                                    {!isDoctor && q.owner === username && (
                                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                            <button onClick={() => deleteQuestion(q.qid)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem' }}>
                                                <Trash2 size={14} /> 删除提问
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default CommunityPage;
