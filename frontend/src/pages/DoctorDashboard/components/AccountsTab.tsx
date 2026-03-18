import React from 'react';
import { UserPlus, RefreshCw, Trash2 } from 'lucide-react';
import type { AuthRole } from '../../../context/AuthContext';
import styles from '../DoctorDashboard.module.css';
import type { ManagedAccount } from '../types';
import { roleLabelMap } from '../types';

interface AccountsTabProps {
    newAccount: { username: string; password: string; role: AuthRole };
    setNewAccount: React.Dispatch<React.SetStateAction<{ username: string; password: string; role: AuthRole }>>;
    createAccount: () => void;
    accountsLoading: boolean;
    accountError: string | null;
    accountNotice: string | null;
    fetchAccounts: () => void;
    accounts: ManagedAccount[];
    username: string | null;
    accountMutationId: number | null;
    updateAccountRole: (account: ManagedAccount, nextRole: AuthRole) => void;
    deleteAccount: (account: ManagedAccount) => void;
}

const AccountsTab: React.FC<AccountsTabProps> = ({
    newAccount, setNewAccount, createAccount, accountsLoading, accountError, accountNotice,
    fetchAccounts, accounts, username, accountMutationId, updateAccountRole, deleteAccount
}) => {
    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.tableCard} style={{ padding: '1.2rem', marginBottom: '1rem' }}>
                <div className={styles.accountFormGrid}>
                    <input 
                        className={styles.formInput} 
                        placeholder="用户名" 
                        value={newAccount.username} 
                        onChange={(event) => setNewAccount((previous) => ({ ...previous, username: event.target.value }))} 
                    />
                    <input 
                        className={styles.formInput} 
                        type="password" 
                        placeholder="初始密码" 
                        value={newAccount.password} 
                        onChange={(event) => setNewAccount((previous) => ({ ...previous, password: event.target.value }))} 
                    />
                    <select 
                        className={styles.formInput} 
                        value={newAccount.role} 
                        onChange={(event) => setNewAccount((previous) => ({ ...previous, role: event.target.value as AuthRole }))}
                    >
                        {Object.entries(roleLabelMap).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                    <button 
                        className={styles.primaryActionBtn} 
                        onClick={() => void createAccount()} 
                        disabled={accountsLoading}
                    ><UserPlus size={16} />新建账号</button>
                </div>
                {(accountError || accountNotice) && <div className={`${styles.noticeBanner} ${accountError ? styles.noticeError : styles.noticeSuccess}`}>{accountError || accountNotice}</div>}
            </div>
            <div className={styles.tableCard}>
                <div className={styles.cardHeader}>
                    <h3>账号列表</h3>
                    <button className={styles.refreshBtn} onClick={() => void fetchAccounts()} disabled={accountsLoading}>
                        <RefreshCw size={16} className={accountsLoading ? 'spin' : ''} />刷新列表
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
                                    <td colSpan={4} className={styles.emptyState}>{accountsLoading ? '正在加载账号列表...' : '暂无账号数据'}</td>
                                </tr>
                            ) : (
                                accounts.map((account) => { 
                                    const isSelf = account.username === username; 
                                    const isLastSuperAdmin = account.role === 'super_admin' && accounts.filter((item) => item.role === 'super_admin').length <= 1; 
                                    const locked = isSelf || isLastSuperAdmin || accountMutationId === account.id; 
                                    return (
                                        <tr key={account.id}>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                                                    <span>{account.username}</span>
                                                    {isSelf && <span className={styles.selfBadge}>当前账号</span>}
                                                </div>
                                            </td>
                                            <td>
                                                <select 
                                                    className={styles.rowSelect} 
                                                    value={account.role} 
                                                    disabled={locked} 
                                                    onChange={(event) => void updateAccountRole(account, event.target.value as AuthRole)}
                                                >
                                                    {Object.entries(roleLabelMap).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                                                </select>
                                            </td>
                                            <td>{new Date(account.created_at).toLocaleString()}</td>
                                            <td>
                                                <button 
                                                    className={`${styles.actionBtn} ${styles.dangerBtn}`} 
                                                    onClick={() => void deleteAccount(account)} 
                                                    disabled={locked}
                                                ><Trash2 size={14} />删除</button>
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
};

export default AccountsTab;
