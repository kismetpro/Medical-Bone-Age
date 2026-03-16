import React from 'react';
import type { RefObject } from 'react';
import { X, Upload } from 'lucide-react';
import styles from '../DoctorDashboard.module.css';
import type { PredictionDetail, PatientUser } from '../types';

interface PredictionModalProps {
    closePredictionModal: () => void;
    predictionForm: { targetUserId: string; gender: 'male' | 'female'; currentHeight: string; realAge: string };
    setPredictionForm: React.Dispatch<React.SetStateAction<{ targetUserId: string; gender: 'male' | 'female'; currentHeight: string; realAge: string }>>;
    patientsLoading: boolean;
    patientUsers: PatientUser[];
    createPrediction: () => void;
    predictionSubmitting: boolean;
    predictionFileInputRef: RefObject<HTMLInputElement | null>;
    loadPredictionFile: (file: File) => void;
    predictionPreview: string | null;
    predictionFile: File | null;
}

export const PredictionModal: React.FC<PredictionModalProps> = ({
    closePredictionModal, predictionForm, setPredictionForm, patientsLoading, patientUsers,
    createPrediction, predictionSubmitting, predictionFileInputRef, loadPredictionFile,
    predictionPreview, predictionFile
}) => {
    const selectedPatient = patientUsers.find((item) => String(item.id) === predictionForm.targetUserId);
    const genderLabel = (value: string) => (value === 'male' ? '男' : '女');

    return (
        <div className={styles.modalOverlay}>
            <div className={styles.modalContent}>
                <div className={styles.modalHeader}>
                    <h3>新增预测记录</h3>
                    <button className={styles.closeBtn} onClick={closePredictionModal}><X size={20} /></button>
                </div>
                <div className={styles.modalBody}>
                    <div className={styles.predictionFormGrid}>
                        <div>
                            <div className={styles.detailBlock}>
                                <h4>选择个人用户</h4>
                                <select 
                                    className={styles.formInput} 
                                    value={predictionForm.targetUserId} 
                                    onChange={(event) => setPredictionForm((previous) => ({ ...previous, targetUserId: event.target.value }))}
                                >
                                    <option value="">{patientsLoading ? '正在加载个人用户...' : '请选择个人用户'}</option>
                                    {patientUsers.map((patient) => <option key={patient.id} value={patient.id}>{patient.username} (UID: {patient.id})</option>)}
                                </select>
                            </div>
                            <div className={styles.detailBlock}>
                                <h4>性别</h4>
                                <div className={styles.genderSwitch}>
                                    <button type="button" className={predictionForm.gender === 'male' ? styles.genderSwitchActive : ''} onClick={() => setPredictionForm((previous) => ({ ...previous, gender: 'male' }))}>男</button>
                                    <button type="button" className={predictionForm.gender === 'female' ? styles.genderSwitchActive : ''} onClick={() => setPredictionForm((previous) => ({ ...previous, gender: 'female' }))}>女</button>
                                </div>
                            </div>
                            <div className={styles.predictionInputGrid}>
                                <input className={styles.formInput} placeholder="当前身高（cm，可选）" value={predictionForm.currentHeight} onChange={(event) => setPredictionForm((previous) => ({ ...previous, currentHeight: event.target.value }))} />
                                <input className={styles.formInput} placeholder="实际年龄（岁，可选）" value={predictionForm.realAge} onChange={(event) => setPredictionForm((previous) => ({ ...previous, realAge: event.target.value }))} />
                            </div>
                            <div className={styles.modalFooter}>
                                <button className={styles.actionBtn} onClick={closePredictionModal}>取消</button>
                                <button className={styles.primaryActionBtn} onClick={() => void createPrediction()} disabled={predictionSubmitting}><Upload size={15} />{predictionSubmitting ? '预测中...' : '开始预测'}</button>
                            </div>
                        </div>
                        <div>
                            <div 
                                className={styles.uploadPanel} 
                                onClick={() => predictionFileInputRef.current?.click()} 
                                onDragOver={(event) => { event.preventDefault(); event.stopPropagation(); }} 
                                onDrop={(event) => { event.preventDefault(); event.stopPropagation(); const file = event.dataTransfer.files?.[0]; if (file) loadPredictionFile(file); }}
                            >
                                {predictionPreview ? <img src={predictionPreview} alt="预测预览" className={styles.uploadPreviewImage} /> : (
                                    <div className={styles.uploadPlaceholder}>
                                        <Upload size={22} /><p>点击或拖拽上传影像文件</p><span>直接复用个人用户预测评估流程</span>
                                    </div>
                                )}
                            </div>
                            <input ref={predictionFileInputRef} type="file" accept="image/*" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) loadPredictionFile(file); }} />
                            <div className={styles.selectionSummary}>
                                <p>个人用户：{selectedPatient ? `${selectedPatient.username} (UID: ${selectedPatient.id})` : '未选择'}</p>
                                <p>性别：{genderLabel(predictionForm.gender)}</p>
                                <p>文件：{predictionFile?.name || '未上传'}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

interface DetailModalProps {
    selectedRecord: PredictionDetail;
    setSelectedRecord: (detail: PredictionDetail | null) => void;
}

export const DetailModal: React.FC<DetailModalProps> = ({ selectedRecord, setSelectedRecord }) => {
    const genderLabel = (value: string) => (value === 'male' ? '男' : '女');

    return (
        <div className={styles.modalOverlay}>
            <div className={styles.modalContent}>
                <div className={styles.modalHeader}>
                    <h3>预测详情 - #{selectedRecord.id.slice(-6)}</h3>
                    <button className={styles.closeBtn} onClick={() => setSelectedRecord(null)}><X size={20} /></button>
                </div>
                <div className={styles.modalBody}>
                    <div className={styles.detailGrid}>
                        <div>
                            <div className={styles.detailBlock}><h4>目标个人用户</h4><p>{selectedRecord.username || '未知用户'}{selectedRecord.user_id ? ` (UID: ${selectedRecord.user_id})` : ''}</p></div>
                            <div className={styles.detailBlock}><h4>预测骨龄</h4><p style={{ color: '#2563eb', fontSize: '1.5rem', fontWeight: 700 }}>{selectedRecord.predicted_age_years.toFixed(1)} 岁</p></div>
                            <div className={styles.detailBlock}><h4>性别</h4><p>{genderLabel(selectedRecord.gender)}</p></div>
                            {selectedRecord.real_age_years != null && <div className={styles.detailBlock}><h4>实际年龄</h4><p>{selectedRecord.real_age_years.toFixed(1)} 岁</p></div>}
                            {selectedRecord.predicted_adult_height != null && <div className={styles.detailBlock}><h4>预测成年身高</h4><p>{selectedRecord.predicted_adult_height.toFixed(1)} cm</p></div>}
                            <div className={styles.detailBlock}>
                                <h4>异常特征</h4>
                                {selectedRecord.anomalies && selectedRecord.anomalies.length > 0 ? (
                                    <ul style={{ color: '#ef4444', margin: '0 0 1rem 0', paddingLeft: '1.2rem' }}>
                                        {selectedRecord.anomalies.map((anomaly, index) => <li key={`${anomaly.type}-${index}`}>{anomaly.type} ({(anomaly.score * 100).toFixed(0)}%)</li>)}
                                    </ul>
                                ) : <p style={{ color: '#16a34a' }}>未发现明显异常特征。</p>}
                            </div>
                            {selectedRecord.rus_chn_details && (
                                <div className={styles.detailBlock}>
                                    <h4>RUS-CHN 评分</h4>
                                    <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                                        <p style={{ margin: 0, fontWeight: 600 }}>总分：{selectedRecord.rus_chn_details.total_score ?? '暂无'}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                        <div>
                            {selectedRecord.heatmap_base64 ? (
                                <div style={{ textAlign: 'center' }}>
                                    <h4 style={{ marginBottom: '0.5rem', color: '#64748b' }}>Grad-CAM 热力图</h4>
                                    <div style={{ position: 'relative', display: 'inline-block' }}>
                                        <img src={selectedRecord.heatmap_base64} alt="GradCAM" className={styles.detailImage} />
                                        {selectedRecord.anomalies?.map((item, index) => item.score > 0.45 ? (
                                            <div key={`${item.type}-${index}`} style={{ left: `${(item.coord[0] - item.coord[2] / 2) * 100}%`, top: `${(item.coord[1] - item.coord[3] / 2) * 100}%`, width: `${item.coord[2] * 100}%`, height: `${item.coord[3] * 100}%`, position: 'absolute', border: '2px solid #ef4444', pointerEvents: 'none' }}>
                                                <span className={styles.anomalyLabel}>{item.type}</span>
                                            </div>
                                        ) : null)}
                                    </div>
                                </div>
                            ) : <div className={styles.emptyDetailPanel}>暂无热力图数据。</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
