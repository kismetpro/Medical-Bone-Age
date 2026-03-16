import React from 'react';
import { Users, Activity, CheckCircle, RefreshCw, Upload, Eye, Trash2 } from 'lucide-react';
import styles from '../DoctorDashboard.module.css';
import type { PredictionRecord, PatientUser } from '../types';

interface RecordsTabProps {
    records: PredictionRecord[];
    patientUsers: PatientUser[];
    displayRole: string;
    loading: boolean;
    patientsLoading: boolean;
    fetchRecords: () => void;
    fetchPatientUsers: () => void;
    setPredictionModalOpen: (open: boolean) => void;
    viewDetails: (id: string) => void;
    deletePredictionRecord: (record: PredictionRecord) => void;
    predictionMutationId: string | null;
}

const RecordsTab: React.FC<RecordsTabProps> = ({
    records, patientUsers, displayRole, loading, patientsLoading,
    fetchRecords, fetchPatientUsers, setPredictionModalOpen,
    viewDetails, deletePredictionRecord, predictionMutationId
}) => {
    const genderLabel = (value: string) => (value === 'male' ? '男' : '女');

    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.statsGrid}>
                <div className={styles.statCard}>
                    <div className={`${styles.statIcon} ${styles.blue}`}><Users size={24} /></div>
                    <div className={styles.statInfo}><h4>记录总数</h4><p>{records.length}</p></div>
                </div>
                <div className={styles.statCard}>
                    <div className={`${styles.statIcon} ${styles.purple}`}><Activity size={24} /></div>
                    <div className={styles.statInfo}><h4>个人用户数</h4><p>{patientUsers.length}</p></div>
                </div>
                <div className={styles.statCard}>
                    <div className={`${styles.statIcon} ${styles.green}`}><CheckCircle size={24} /></div>
                    <div className={styles.statInfo}><h4>当前角色</h4><p style={{ fontSize: '1rem' }}>{displayRole}</p></div>
                </div>
            </div>

            <div className={styles.tableCard}>
                <div className={styles.cardHeader}>
                    <h3>近期预测记录</h3>
                    <div className={styles.headerActions}>
                        <button className={styles.refreshBtn} onClick={() => void fetchPatientUsers()} disabled={patientsLoading}>
                            <RefreshCw size={16} className={patientsLoading ? 'spin' : ''} />刷新用户
                        </button>
                        <button className={styles.refreshBtn} onClick={() => void fetchRecords()} disabled={loading}>
                            <RefreshCw size={16} className={loading ? 'spin' : ''} />刷新列表
                        </button>
                        <button className={styles.primaryActionBtn} onClick={() => setPredictionModalOpen(true)}>
                            <Upload size={16} />新增预测记录
                        </button>
                    </div>
                </div>
                <div className={styles.tableWrapper}>
                    <table>
                        <thead>
                            <tr>
                                <th>记录 ID</th>
                                <th>日期时间</th>
                                <th>个人用户</th>
                                <th>用户 ID</th>
                                <th>性别</th>
                                <th>预测骨龄</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {records.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className={styles.emptyState}>
                                        {loading ? '正在加载预测记录...' : '暂无预测记录'}
                                    </td>
                                </tr>
                            ) : (
                                records.map((record) => (
                                    <tr key={record.id}>
                                        <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', color: '#64748b' }}>#{record.id.slice(0, 8)}</td>
                                        <td>{new Date(record.timestamp).toLocaleString()}</td>
                                        <td>{record.username || '未知用户'}</td>
                                        <td>UID: {record.user_id}</td>
                                        <td>
                                            <span className={`${styles.genderTag} ${record.gender === 'male' ? styles.male : styles.female}`}>
                                                {genderLabel(record.gender)}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 600 }}>{record.predicted_age_years.toFixed(1)} 岁</td>
                                        <td>
                                            <div className={styles.rowActions}>
                                                <button className={styles.actionBtn} onClick={() => void viewDetails(record.id)}><Eye size={14} />查看详情</button>
                                                <button 
                                                    className={`${styles.actionBtn} ${styles.dangerBtn}`} 
                                                    onClick={() => void deletePredictionRecord(record)} 
                                                    disabled={predictionMutationId === record.id}
                                                >
                                                    <Trash2 size={14} />删除
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default RecordsTab;
