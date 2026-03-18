import React from 'react';
import type { RefObject } from 'react';
import { Bot, HelpCircle, Send, FileSpreadsheet, MessageCircle, Upload, Plus, Trash2 } from 'lucide-react';
import styles from '../UserDashboard.module.css';

interface CommunityTabProps {
    consultMessages: Array<{ role: 'user' | 'assistant', text: string }>;
    consultInput: string;
    setConsultInput: (text: string) => void;
    sendConsult: () => void;
    consultLoading: boolean;
    articles: any[];
    qaList: any[];
    qaLoading: boolean;
    fetchQaList: () => void;
    qaText: string;
    setQaText: (text: string) => void;
    qaImageInputRef: RefObject<HTMLInputElement | null>;
    handleQaImageSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
    qaImageBase64: string | null;
    submitQuestion: () => void;
    qaSubmitting: boolean;
    deleteQuestion: (id: number) => void;
}

const CommunityTab: React.FC<CommunityTabProps> = ({
    consultMessages, consultInput, setConsultInput, sendConsult, consultLoading,
    articles, qaList, qaLoading, fetchQaList, qaText, setQaText,
    qaImageInputRef, handleQaImageSelect, qaImageBase64, submitQuestion,
    qaSubmitting, deleteQuestion
}) => {
    return (
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>

            {/* ─── 智能问诊区 ─── */}
            <div className={styles.communityPanel}>
                <div className={styles.communityPanelHeader}>
                    <Bot size={18} color="#3b82f6" />
                    <h3>智能健康问诊</h3>
                    <span className={styles.aiTag}>AI 驱动</span>
                </div>
                <p className={styles.communityDesc}>向 AI 健康顾问咨询骨龄发育、生长规律等问题。AI 提供科普参考，不替代医生诊断。</p>
                <div className={styles.chatWindow}>
                    {consultMessages.length === 0 && (
                        <div className={styles.chatEmpty}>
                            <HelpCircle size={32} color="#cbd5e1" />
                            <p>输入您的问题，AI 将为您解答骨龄发育相关健康知识。</p>
                        </div>
                    )}
                    {consultMessages.map((m, idx) => (
                        <div key={idx} className={`${styles.chatMsg} ${m.role === 'user' ? styles.chatMsgUser : styles.chatMsgAi}`}>
                            <div className={styles.chatMsgRole}>{m.role === 'user' ? '您' : 'AI 顾问'}</div>
                            <div className={styles.chatMsgText}>{m.text}</div>
                        </div>
                    ))}
                </div>
                <div className={styles.chatInputRow}>
                    <textarea
                        className={styles.chatTextarea}
                        placeholder="例如：孩子骨龄超前一岁需要担心吗？"
                        value={consultInput}
                        onChange={e => setConsultInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendConsult(); } }}
                        rows={2}
                    />
                    <button className={styles.chatSendBtn} onClick={sendConsult} disabled={consultLoading}>
                        <Send size={16} />{consultLoading ? ' 思考中...' : ' 发送'}
                    </button>
                </div>
            </div>

            {/* ─── 专家科普文章区 ─── */}
            <div className={styles.communityPanel}>
                <div className={styles.communityPanelHeader}>
                    <FileSpreadsheet size={18} color="#3b82f6" />
                    <h3>专家健康科普文章</h3>
                </div>
                {articles.length === 0 ? (
                    <p className={styles.communityEmpty}>目前平台上医生还未发布相关科普文章。</p>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {articles.map(article => (
                            <div key={article.id} className={styles.articleCard}>
                                <h4 className={styles.articleTitle}>{article.title}</h4>
                                <p className={styles.articleMeta}>发布者：{article.author_name} 医生 • {new Date(article.created_at).toLocaleDateString()}</p>
                                <p className={styles.articleContent}>{article.content}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ─── 问答论坛区 ─── */}
            <div className={styles.communityPanel}>
                <div className={styles.communityPanelHeader}>
                    <MessageCircle size={18} color="#3b82f6" />
                    <h3>问答论坛</h3>
                    <button className={styles.refreshSmallBtn} onClick={fetchQaList} disabled={qaLoading}>
                        刷新
                    </button>
                </div>
                <p className={styles.communityDesc}>在此向医生提出专业问题，附上影像以便医生参考，医生将在此页面回复您。</p>

                {/* 发帖表单 */}
                <div className={styles.qaForm}>
                    <textarea
                        className={styles.qaTextarea}
                        placeholder="描述您的问题，例如：孩子7岁，骨龄测定为8.5岁，是否需要就医？"
                        value={qaText}
                        onChange={e => setQaText(e.target.value)}
                        rows={3}
                    />
                    <div className={styles.qaFormActions}>
                        <div className={styles.qaImageSelect}>
                            <input
                                type="file" accept="image/*" style={{ display: 'none' }}
                                ref={qaImageInputRef}
                                onChange={handleQaImageSelect}
                            />
                            <button className={styles.qaImageBtn} onClick={() => qaImageInputRef.current?.click()}>
                                <Upload size={14} /> {qaImageBase64 ? '✅ 已选择图片' : '附上影像'}
                            </button>
                            {qaImageBase64 && (
                                <img src={qaImageBase64} alt="附件预览" className={styles.qaImageThumb} />
                            )}
                        </div>
                        <button
                            className={styles.qaSubmitBtn}
                            onClick={submitQuestion}
                            disabled={qaSubmitting || !qaText.trim() || !qaImageBase64}
                        >
                            <Plus size={14} /> {qaSubmitting ? '提交中...' : '提交问题'}
                        </button>
                    </div>
                </div>

                {/* 问题列表 */}
                <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    {qaLoading && <p className={styles.communityEmpty}>加载中...</p>}
                    {!qaLoading && qaList.length === 0 && (
                        <p className={styles.communityEmpty}>您还没有提交任何问题。</p>
                    )}
                    {qaList.map(q => (
                        <div key={q.qid} className={styles.qaCard}>
                            <div className={styles.qaCardHeader}>
                                <span className={styles.qaTime}>{new Date(q.createTime).toLocaleString()}</span>
                                {q.reply ? (
                                    <span className={styles.qaRepliedBadge}>已回复</span>
                                ) : (
                                    <span className={styles.qaPendingBadge}>待回复</span>
                                )}
                                <button className={styles.qaDeleteBtn} onClick={() => deleteQuestion(q.qid)} title="删除">
                                    <Trash2 size={13} />
                                </button>
                            </div>
                            <div className={styles.qaQuestion}>
                                <strong>我的问题：</strong>{q.text}
                            </div>
                            {q.image && (
                                <img src={q.image} alt="附件" className={styles.qaCardImage} />
                            )}
                            {q.reply && (
                                <div className={styles.qaReply}>
                                    <strong>医生回复：</strong>{q.reply}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

        </div>
    );
};

export default CommunityTab;
