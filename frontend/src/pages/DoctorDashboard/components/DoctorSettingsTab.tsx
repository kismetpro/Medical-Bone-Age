import React, { useState } from 'react';
import { User, Lock, Bell, Shield, Database, Trash2, Save, Eye, EyeOff, Users, Key } from 'lucide-react';
import styles from './DoctorSettingsTab.module.css';

interface DoctorSettingsTabProps {
    username: string | null;
    isSuperAdmin: boolean;
    onUpdateSuccess?: () => void;
}

const DoctorSettingsTab: React.FC<DoctorSettingsTabProps> = ({ username, isSuperAdmin, onUpdateSuccess }) => {
    const [activeSection, setActiveSection] = useState<'profile' | 'security' | 'notifications' | 'data' | 'admin'>('profile');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    // 个人信息表单
    const [profileForm, setProfileForm] = useState({
        username: username || '',
        email: '',
        phone: '',
        department: '',
        title: ''
    });

    // 密码修改表单
    const [passwordForm, setPasswordForm] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });
    const [showPasswords, setShowPasswords] = useState({
        current: false,
        new: false,
        confirm: false
    });

    // 通知设置
    const [notificationSettings, setNotificationSettings] = useState({
        emailNotifications: true,
        smsNotifications: false,
        pushNotifications: true,
        patientAlerts: true,
        systemUpdates: false
    });

    // 管理员设置
    const [adminSettings, setAdminSettings] = useState({
        doctorSelfRegister: true,
        requireRegistrationKey: false,
        registrationKey: ''
    });

    const showMessage = (type: 'success' | 'error', text: string) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 3000);
    };

    const handleProfileUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        // 模拟API调用
        setTimeout(() => {
            setLoading(false);
            showMessage('success', '个人信息更新成功');
            if (onUpdateSuccess) onUpdateSuccess();
        }, 1000);
    };

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            showMessage('error', '两次输入的密码不一致');
            return;
        }
        
        if (passwordForm.newPassword.length < 8) {
            showMessage('error', '密码长度至少为8位');
            return;
        }

        setLoading(true);
        
        // 模拟API调用
        setTimeout(() => {
            setLoading(false);
            setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
            showMessage('success', '密码修改成功');
        }, 1000);
    };

    const handleNotificationUpdate = async () => {
        setLoading(true);
        
        // 模拟API调用
        setTimeout(() => {
            setLoading(false);
            showMessage('success', '通知设置已更新');
        }, 1000);
    };

    const handleAdminSettingsUpdate = async () => {
        setLoading(true);
        
        // 模拟API调用
        setTimeout(() => {
            setLoading(false);
            showMessage('success', '管理员设置已更新');
        }, 1000);
    };

    const handleDataClear = async () => {
        if (!window.confirm('确定要清除所有本地数据吗？此操作不可恢复。')) {
            return;
        }
        
        setLoading(true);
        
        // 清除本地存储
        localStorage.clear();
        sessionStorage.clear();
        
        setTimeout(() => {
            setLoading(false);
            showMessage('success', '本地数据已清除');
        }, 1000);
    };

    return (
        <div className={styles.settingsContainer}>
            <div className={styles.settingsLayout}>
                {/* 左侧菜单 */}
                <aside className={styles.settingsSidebar}>
                    <h3>设置</h3>
                    <nav>
                        <button 
                            className={activeSection === 'profile' ? styles.active : ''} 
                            onClick={() => setActiveSection('profile')}
                        >
                            <User size={18} /> 个人信息
                        </button>
                        <button 
                            className={activeSection === 'security' ? styles.active : ''} 
                            onClick={() => setActiveSection('security')}
                        >
                            <Lock size={18} /> 安全设置
                        </button>
                        <button 
                            className={activeSection === 'notifications' ? styles.active : ''} 
                            onClick={() => setActiveSection('notifications')}
                        >
                            <Bell size={18} /> 通知设置
                        </button>
                        {isSuperAdmin && (
                            <button 
                                className={activeSection === 'admin' ? styles.active : ''} 
                                onClick={() => setActiveSection('admin')}
                            >
                                <Shield size={18} /> 管理员设置
                            </button>
                        )}
                        <button 
                            className={activeSection === 'data' ? styles.active : ''} 
                            onClick={() => setActiveSection('data')}
                        >
                            <Database size={18} /> 数据管理
                        </button>
                    </nav>
                </aside>

                {/* 右侧内容 */}
                <main className={styles.settingsContent}>
                    {message && (
                        <div className={`${styles.message} ${styles[message.type]}`}>
                            {message.text}
                        </div>
                    )}

                    {/* 个人信息 */}
                    {activeSection === 'profile' && (
                        <div className={styles.section}>
                            <h2>个人信息</h2>
                            <form onSubmit={handleProfileUpdate} className={styles.form}>
                                <div className={styles.formGroup}>
                                    <label>用户名</label>
                                    <input 
                                        type="text" 
                                        value={profileForm.username}
                                        disabled
                                        className={styles.disabledInput}
                                    />
                                    <small>用户名不可修改</small>
                                </div>
                                <div className={styles.formGroup}>
                                    <label>邮箱地址</label>
                                    <input 
                                        type="email" 
                                        value={profileForm.email}
                                        onChange={(e) => setProfileForm({...profileForm, email: e.target.value})}
                                        placeholder="请输入邮箱地址"
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>手机号码</label>
                                    <input 
                                        type="tel" 
                                        value={profileForm.phone}
                                        onChange={(e) => setProfileForm({...profileForm, phone: e.target.value})}
                                        placeholder="请输入手机号码"
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>所属科室</label>
                                    <input 
                                        type="text" 
                                        value={profileForm.department}
                                        onChange={(e) => setProfileForm({...profileForm, department: e.target.value})}
                                        placeholder="请输入所属科室"
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>职称</label>
                                    <input 
                                        type="text" 
                                        value={profileForm.title}
                                        onChange={(e) => setProfileForm({...profileForm, title: e.target.value})}
                                        placeholder="请输入职称"
                                    />
                                </div>
                                <button type="submit" className={styles.submitBtn} disabled={loading}>
                                    <Save size={18} /> {loading ? '保存中...' : '保存更改'}
                                </button>
                            </form>
                        </div>
                    )}

                    {/* 安全设置 */}
                    {activeSection === 'security' && (
                        <div className={styles.section}>
                            <h2>安全设置</h2>
                            <form onSubmit={handlePasswordChange} className={styles.form}>
                                <div className={styles.formGroup}>
                                    <label>当前密码</label>
                                    <div className={styles.passwordInput}>
                                        <input 
                                            type={showPasswords.current ? 'text' : 'password'}
                                            value={passwordForm.currentPassword}
                                            onChange={(e) => setPasswordForm({...passwordForm, currentPassword: e.target.value})}
                                            placeholder="请输入当前密码"
                                            required
                                        />
                                        <button 
                                            type="button"
                                            onClick={() => setShowPasswords({...showPasswords, current: !showPasswords.current})}
                                        >
                                            {showPasswords.current ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    </div>
                                </div>
                                <div className={styles.formGroup}>
                                    <label>新密码</label>
                                    <div className={styles.passwordInput}>
                                        <input 
                                            type={showPasswords.new ? 'text' : 'password'}
                                            value={passwordForm.newPassword}
                                            onChange={(e) => setPasswordForm({...passwordForm, newPassword: e.target.value})}
                                            placeholder="请输入新密码（至少8位）"
                                            required
                                        />
                                        <button 
                                            type="button"
                                            onClick={() => setShowPasswords({...showPasswords, new: !showPasswords.new})}
                                        >
                                            {showPasswords.new ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    </div>
                                </div>
                                <div className={styles.formGroup}>
                                    <label>确认新密码</label>
                                    <div className={styles.passwordInput}>
                                        <input 
                                            type={showPasswords.confirm ? 'text' : 'password'}
                                            value={passwordForm.confirmPassword}
                                            onChange={(e) => setPasswordForm({...passwordForm, confirmPassword: e.target.value})}
                                            placeholder="请再次输入新密码"
                                            required
                                        />
                                        <button 
                                            type="button"
                                            onClick={() => setShowPasswords({...showPasswords, confirm: !showPasswords.confirm})}
                                        >
                                            {showPasswords.confirm ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    </div>
                                </div>
                                <div className={styles.securityTips}>
                                    <Shield size={16} />
                                    <div>
                                        <strong>安全提示：</strong>
                                        <ul>
                                            <li>密码长度至少8位，建议包含大小写字母、数字和特殊字符</li>
                                            <li>不要使用与其他网站相同的密码</li>
                                            <li>定期更换密码以保护账户安全</li>
                                            <li>作为医疗专业人员，请特别注意账户安全</li>
                                        </ul>
                                    </div>
                                </div>
                                <button type="submit" className={styles.submitBtn} disabled={loading}>
                                    <Save size={18} /> {loading ? '修改中...' : '修改密码'}
                                </button>
                            </form>
                        </div>
                    )}

                    {/* 通知设置 */}
                    {activeSection === 'notifications' && (
                        <div className={styles.section}>
                            <h2>通知设置</h2>
                            <div className={styles.notificationSettings}>
                                <div className={styles.notificationItem}>
                                    <div className={styles.notificationInfo}>
                                        <strong>邮件通知</strong>
                                        <p>接收重要更新和提醒的邮件通知</p>
                                    </div>
                                    <label className={styles.switch}>
                                        <input 
                                            type="checkbox"
                                            checked={notificationSettings.emailNotifications}
                                            onChange={(e) => setNotificationSettings({...notificationSettings, emailNotifications: e.target.checked})}
                                        />
                                        <span></span>
                                    </label>
                                </div>
                                <div className={styles.notificationItem}>
                                    <div className={styles.notificationInfo}>
                                        <strong>短信通知</strong>
                                        <p>接收紧急事件的短信通知</p>
                                    </div>
                                    <label className={styles.switch}>
                                        <input 
                                            type="checkbox"
                                            checked={notificationSettings.smsNotifications}
                                            onChange={(e) => setNotificationSettings({...notificationSettings, smsNotifications: e.target.checked})}
                                        />
                                        <span></span>
                                    </label>
                                </div>
                                <div className={styles.notificationItem}>
                                    <div className={styles.notificationInfo}>
                                        <strong>推送通知</strong>
                                        <p>在浏览器中接收推送通知</p>
                                    </div>
                                    <label className={styles.switch}>
                                        <input 
                                            type="checkbox"
                                            checked={notificationSettings.pushNotifications}
                                            onChange={(e) => setNotificationSettings({...notificationSettings, pushNotifications: e.target.checked})}
                                        />
                                        <span></span>
                                    </label>
                                </div>
                                <div className={styles.notificationItem}>
                                    <div className={styles.notificationInfo}>
                                        <strong>患者提醒</strong>
                                        <p>接收新患者注册和重要患者状态的提醒</p>
                                    </div>
                                    <label className={styles.switch}>
                                        <input 
                                            type="checkbox"
                                            checked={notificationSettings.patientAlerts}
                                            onChange={(e) => setNotificationSettings({...notificationSettings, patientAlerts: e.target.checked})}
                                        />
                                        <span></span>
                                    </label>
                                </div>
                                <div className={styles.notificationItem}>
                                    <div className={styles.notificationInfo}>
                                        <strong>系统更新</strong>
                                        <p>接收系统功能更新和维护通知</p>
                                    </div>
                                    <label className={styles.switch}>
                                        <input 
                                            type="checkbox"
                                            checked={notificationSettings.systemUpdates}
                                            onChange={(e) => setNotificationSettings({...notificationSettings, systemUpdates: e.target.checked})}
                                        />
                                        <span></span>
                                    </label>
                                </div>
                            </div>
                            <button 
                                className={styles.submitBtn} 
                                onClick={handleNotificationUpdate}
                                disabled={loading}
                            >
                                <Save size={18} /> {loading ? '保存中...' : '保存设置'}
                            </button>
                        </div>
                    )}

                    {/* 管理员设置 */}
                    {activeSection === 'admin' && (
                        <div className={styles.section}>
                            <h2>管理员设置</h2>
                            <div className={styles.adminSettings}>
                                <div className={styles.adminCard}>
                                    <div className={styles.adminHeader}>
                                        <Users size={20} />
                                        <strong>医生注册管理</strong>
                                    </div>
                                    <div className={styles.adminContent}>
                                        <div className={styles.adminItem}>
                                            <label>允许医生自注册</label>
                                            <label className={styles.switch}>
                                                <input 
                                                    type="checkbox"
                                                    checked={adminSettings.doctorSelfRegister}
                                                    onChange={(e) => setAdminSettings({...adminSettings, doctorSelfRegister: e.target.checked})}
                                                />
                                                <span></span>
                                            </label>
                                        </div>
                                        <div className={styles.adminItem}>
                                            <label>需要注册密钥</label>
                                            <label className={styles.switch}>
                                                <input 
                                                    type="checkbox"
                                                    checked={adminSettings.requireRegistrationKey}
                                                    onChange={(e) => setAdminSettings({...adminSettings, requireRegistrationKey: e.target.checked})}
                                                />
                                                <span></span>
                                            </label>
                                        </div>
                                        <div className={styles.adminItem}>
                                            <label>注册密钥</label>
                                            <div className={styles.keyInput}>
                                                <input 
                                                    type="password" 
                                                    value={adminSettings.registrationKey}
                                                    onChange={(e) => setAdminSettings({...adminSettings, registrationKey: e.target.value})}
                                                    placeholder="设置医生注册密钥"
                                                    disabled={!adminSettings.requireRegistrationKey}
                                                />
                                                <Key size={18} />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <button 
                                className={styles.submitBtn} 
                                onClick={handleAdminSettingsUpdate}
                                disabled={loading}
                            >
                                <Save size={18} /> {loading ? '保存中...' : '保存设置'}
                            </button>
                        </div>
                    )}

                    {/* 数据管理 */}
                    {activeSection === 'data' && (
                        <div className={styles.section}>
                            <h2>数据管理</h2>
                            <div className={styles.dataManagement}>
                                <div className={styles.dataCard}>
                                    <h3>本地数据</h3>
                                    <p>清除浏览器中存储的所有本地数据，包括缓存、历史记录等。</p>
                                    <button 
                                        className={styles.dangerBtn}
                                        onClick={handleDataClear}
                                        disabled={loading}
                                    >
                                        <Trash2 size={18} /> {loading ? '清除中...' : '清除本地数据'}
                                    </button>
                                </div>
                                <div className={styles.dataCard}>
                                    <h3>系统数据</h3>
                                    <p>管理系统中的患者数据、预测记录等。此操作需要管理员权限。</p>
                                    <div className={styles.dataActions}>
                                        <button className={styles.secondaryBtn}>
                                            数据备份
                                        </button>
                                        <button className={styles.secondaryBtn}>
                                            数据恢复
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
};

export default DoctorSettingsTab;