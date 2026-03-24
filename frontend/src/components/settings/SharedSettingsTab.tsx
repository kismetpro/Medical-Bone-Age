import { useEffect, useMemo, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Bell,
  Database,
  Eye,
  EyeOff,
  Key,
  Lock,
  Save,
  Shield,
  Trash2,
  User,
  Users,
} from 'lucide-react';
import OverlayDialog from '../dialog/OverlayDialog';
import { useTimedMessage } from '../../hooks/useTimedMessage';
import styles from './SharedSettingsTab.module.css';

type SharedSettingsMode = 'user' | 'doctor';
type SettingsSection = 'profile' | 'security' | 'notifications' | 'data' | 'admin';

interface SharedSettingsTabProps {
  username: string | null;
  mode: SharedSettingsMode;
  isSuperAdmin?: boolean;
  onUpdateSuccess?: () => void;
}

interface SettingsSectionItem {
  id: SettingsSection;
  label: string;
  icon: LucideIcon;
}

interface ProfileFormState {
  username: string;
  email: string;
  phone: string;
  department: string;
  title: string;
}

interface PasswordVisibilityState {
  current: boolean;
  next: boolean;
  confirm: boolean;
}

interface PasswordFormState {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

interface NotificationSettingsState {
  emailNotifications: boolean;
  smsNotifications: boolean;
  pushNotifications: boolean;
  patientAlerts: boolean;
  systemUpdates: boolean;
}

interface AdminSettingsState {
  doctorSelfRegister: boolean;
  requireRegistrationKey: boolean;
  registrationKey: string;
}

interface NotificationItemConfig {
  key: keyof NotificationSettingsState;
  title: string;
  description: string;
}

const WAIT_TIME_MS = 700;

function waitForMockRequest() {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, WAIT_TIME_MS);
  });
}

function createInitialProfileForm(username: string | null): ProfileFormState {
  return {
    username: username ?? '',
    email: '',
    phone: '',
    department: '',
    title: '',
  };
}

function createInitialNotifications(mode: SharedSettingsMode): NotificationSettingsState {
  return {
    emailNotifications: true,
    smsNotifications: false,
    pushNotifications: true,
    patientAlerts: mode === 'doctor',
    systemUpdates: false,
  };
}

export default function SharedSettingsTab({
  username,
  mode,
  isSuperAdmin = false,
  onUpdateSuccess,
}: SharedSettingsTabProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
  const [loading, setLoading] = useState(false);
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);
  const [profileForm, setProfileForm] = useState<ProfileFormState>(() => createInitialProfileForm(username));
  const [passwordForm, setPasswordForm] = useState<PasswordFormState>({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [showPasswords, setShowPasswords] = useState<PasswordVisibilityState>({
    current: false,
    next: false,
    confirm: false,
  });
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettingsState>(
    () => createInitialNotifications(mode),
  );
  const [adminSettings, setAdminSettings] = useState<AdminSettingsState>({
    doctorSelfRegister: true,
    requireRegistrationKey: false,
    registrationKey: '',
  });
  const { message, showMessage } = useTimedMessage();

  useEffect(() => {
    setProfileForm((previous) => ({
      ...previous,
      username: username ?? '',
    }));
  }, [username]);

  useEffect(() => {
    if (!isSuperAdmin && activeSection === 'admin') {
      setActiveSection('profile');
    }
  }, [activeSection, isSuperAdmin]);

  const sections = useMemo<SettingsSectionItem[]>(() => {
    const items: SettingsSectionItem[] = [
      { id: 'profile', label: '个人信息', icon: User },
      { id: 'security', label: '安全设置', icon: Lock },
      { id: 'notifications', label: '通知设置', icon: Bell },
      { id: 'data', label: '数据管理', icon: Database },
    ];

    if (mode === 'doctor' && isSuperAdmin) {
      items.splice(3, 0, { id: 'admin', label: '管理员设置', icon: Shield });
    }

    return items;
  }, [isSuperAdmin, mode]);

  const securityTips = mode === 'doctor'
    ? [
        '密码长度至少 8 位，建议包含大小写字母、数字和特殊字符。',
        '不要和其他网站复用密码。',
        '作为医疗专业人员，请避免在公共设备上长期保持登录。',
      ]
    : [
        '密码长度至少 8 位，建议包含大小写字母、数字和特殊字符。',
        '不要和其他网站复用密码。',
        '定期更换密码有助于保护个人健康档案。',
      ];

  const notificationItems: NotificationItemConfig[] = mode === 'doctor'
    ? [
        { key: 'emailNotifications', title: '邮件通知', description: '接收重要更新和提醒的邮件通知。' },
        { key: 'smsNotifications', title: '短信通知', description: '接收紧急事件的短信通知。' },
        { key: 'pushNotifications', title: '推送通知', description: '在浏览器中接收实时推送。' },
        { key: 'patientAlerts', title: '患者提醒', description: '接收新患者注册和关键状态提醒。' },
        { key: 'systemUpdates', title: '系统更新', description: '接收维护计划和版本更新通知。' },
      ]
    : [
        { key: 'emailNotifications', title: '邮件通知', description: '接收重要更新和健康提醒。' },
        { key: 'smsNotifications', title: '短信通知', description: '接收紧急事件和预约提醒。' },
        { key: 'pushNotifications', title: '推送通知', description: '在浏览器中接收实时提醒。' },
      ];

  const handleProfileUpdate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);

    try {
      await waitForMockRequest();
      showMessage('success', '个人信息更新成功');
      onUpdateSuccess?.();
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      showMessage('error', '两次输入的密码不一致');
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      showMessage('error', '密码长度至少为 8 位');
      return;
    }

    setLoading(true);
    try {
      await waitForMockRequest();
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      showMessage('success', '密码修改成功');
    } finally {
      setLoading(false);
    }
  };

  const handleNotificationUpdate = async () => {
    setLoading(true);
    try {
      await waitForMockRequest();
      showMessage('success', '通知设置已更新');
    } finally {
      setLoading(false);
    }
  };

  const handleAdminSettingsUpdate = async () => {
    setLoading(true);
    try {
      await waitForMockRequest();
      showMessage('success', '管理员设置已更新');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmClearData = async () => {
    setLoading(true);
    setConfirmClearOpen(false);

    try {
      localStorage.clear();
      sessionStorage.clear();
      await waitForMockRequest();
      showMessage('success', '本地数据已清除');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.settingsContainer}>
      <div className={styles.settingsLayout}>
        <aside className={styles.settingsSidebar}>
          <h3>{mode === 'doctor' ? '工作台设置' : '账号设置'}</h3>
          <nav>
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={activeSection === id ? styles.active : undefined}
                onClick={() => setActiveSection(id)}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <main className={styles.settingsContent}>
          {message ? (
            <div className={`${styles.message} ${message.type === 'success' ? styles.success : styles.error}`}>
              {message.text}
            </div>
          ) : null}

          {activeSection === 'profile' ? (
            <section className={styles.section}>
              <h2>个人信息</h2>
              <form className={styles.form} onSubmit={handleProfileUpdate}>
                <div className={styles.formGroup}>
                  <label>用户名</label>
                  <input type="text" value={profileForm.username} disabled className={styles.disabledInput} />
                  <small>用户名不可修改。</small>
                </div>
                <div className={styles.formGroup}>
                  <label>邮箱地址</label>
                  <input
                    type="email"
                    value={profileForm.email}
                    onChange={(event) => setProfileForm((previous) => ({ ...previous, email: event.target.value }))}
                    placeholder="请输入邮箱地址"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>手机号码</label>
                  <input
                    type="tel"
                    value={profileForm.phone}
                    onChange={(event) => setProfileForm((previous) => ({ ...previous, phone: event.target.value }))}
                    placeholder="请输入手机号码"
                  />
                </div>
                {mode === 'doctor' ? (
                  <>
                    <div className={styles.formGroup}>
                      <label>所属科室</label>
                      <input
                        type="text"
                        value={profileForm.department}
                        onChange={(event) =>
                          setProfileForm((previous) => ({ ...previous, department: event.target.value }))
                        }
                        placeholder="请输入所属科室"
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>职称</label>
                      <input
                        type="text"
                        value={profileForm.title}
                        onChange={(event) => setProfileForm((previous) => ({ ...previous, title: event.target.value }))}
                        placeholder="请输入职称"
                      />
                    </div>
                  </>
                ) : null}
                <button type="submit" className={styles.submitBtn} disabled={loading}>
                  <Save size={18} />
                  {loading ? '保存中...' : '保存更改'}
                </button>
              </form>
            </section>
          ) : null}

          {activeSection === 'security' ? (
            <section className={styles.section}>
              <h2>安全设置</h2>
              <form className={styles.form} onSubmit={handlePasswordChange}>
                <div className={styles.formGroup}>
                  <label>当前密码</label>
                  <div className={styles.passwordInput}>
                    <input
                      type={showPasswords.current ? 'text' : 'password'}
                      value={passwordForm.currentPassword}
                      onChange={(event) =>
                        setPasswordForm((previous) => ({ ...previous, currentPassword: event.target.value }))
                      }
                      placeholder="请输入当前密码"
                      required
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowPasswords((previous) => ({ ...previous, current: !previous.current }))
                      }
                    >
                      {showPasswords.current ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label>新密码</label>
                  <div className={styles.passwordInput}>
                    <input
                      type={showPasswords.next ? 'text' : 'password'}
                      value={passwordForm.newPassword}
                      onChange={(event) =>
                        setPasswordForm((previous) => ({ ...previous, newPassword: event.target.value }))
                      }
                      placeholder="请输入新密码（至少 8 位）"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords((previous) => ({ ...previous, next: !previous.next }))}
                    >
                      {showPasswords.next ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label>确认新密码</label>
                  <div className={styles.passwordInput}>
                    <input
                      type={showPasswords.confirm ? 'text' : 'password'}
                      value={passwordForm.confirmPassword}
                      onChange={(event) =>
                        setPasswordForm((previous) => ({ ...previous, confirmPassword: event.target.value }))
                      }
                      placeholder="请再次输入新密码"
                      required
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowPasswords((previous) => ({ ...previous, confirm: !previous.confirm }))
                      }
                    >
                      {showPasswords.confirm ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className={styles.securityTips}>
                  <Shield size={16} />
                  <div>
                    <strong>安全提示</strong>
                    <ul>
                      {securityTips.map((tip) => (
                        <li key={tip}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <button type="submit" className={styles.submitBtn} disabled={loading}>
                  <Save size={18} />
                  {loading ? '修改中...' : '修改密码'}
                </button>
              </form>
            </section>
          ) : null}

          {activeSection === 'notifications' ? (
            <section className={styles.section}>
              <h2>通知设置</h2>
              <div className={styles.notificationSettings}>
                {notificationItems.map(({ key, title, description }) => (
                  <div className={styles.notificationItem} key={key}>
                    <div className={styles.notificationInfo}>
                      <strong>{title}</strong>
                      <p>{description}</p>
                    </div>
                    <label className={styles.switch}>
                      <input
                        type="checkbox"
                        checked={notificationSettings[key as keyof NotificationSettingsState] as boolean}
                        onChange={(event) =>
                          setNotificationSettings((previous) => ({
                            ...previous,
                            [key]: event.target.checked,
                          }))
                        }
                      />
                      <span />
                    </label>
                  </div>
                ))}
              </div>
              <button type="button" className={styles.submitBtn} disabled={loading} onClick={handleNotificationUpdate}>
                <Save size={18} />
                {loading ? '保存中...' : '保存设置'}
              </button>
            </section>
          ) : null}

          {activeSection === 'admin' && mode === 'doctor' && isSuperAdmin ? (
            <section className={styles.section}>
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
                          onChange={(event) =>
                            setAdminSettings((previous) => ({
                              ...previous,
                              doctorSelfRegister: event.target.checked,
                            }))
                          }
                        />
                        <span />
                      </label>
                    </div>
                    <div className={styles.adminItem}>
                      <label>需要注册密钥</label>
                      <label className={styles.switch}>
                        <input
                          type="checkbox"
                          checked={adminSettings.requireRegistrationKey}
                          onChange={(event) =>
                            setAdminSettings((previous) => ({
                              ...previous,
                              requireRegistrationKey: event.target.checked,
                            }))
                          }
                        />
                        <span />
                      </label>
                    </div>
                    <div className={styles.formGroup}>
                      <label>注册密钥</label>
                      <div className={styles.keyInput}>
                        <input
                          type="password"
                          value={adminSettings.registrationKey}
                          onChange={(event) =>
                            setAdminSettings((previous) => ({
                              ...previous,
                              registrationKey: event.target.value,
                            }))
                          }
                          placeholder="设置医生注册密钥"
                          disabled={!adminSettings.requireRegistrationKey}
                        />
                        <Key size={18} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <button type="button" className={styles.submitBtn} disabled={loading} onClick={handleAdminSettingsUpdate}>
                <Save size={18} />
                {loading ? '保存中...' : '保存设置'}
              </button>
            </section>
          ) : null}

          {activeSection === 'data' ? (
            <section className={styles.section}>
              <h2>数据管理</h2>
              <div className={styles.dataManagement}>
                <div className={styles.dataCard}>
                  <h3>本地数据</h3>
                  <p>清除浏览器中保存的缓存、历史记录和临时配置，不影响云端数据。</p>
                  <button
                    type="button"
                    className={styles.dangerBtn}
                    disabled={loading}
                    onClick={() => setConfirmClearOpen(true)}
                  >
                    <Trash2 size={18} />
                    {loading ? '清除中...' : '清除本地数据'}
                  </button>
                </div>
                <div className={styles.dataCard}>
                  {mode === 'doctor' ? (
                    <>
                      <h3>系统数据</h3>
                      <p>管理系统中的患者资料、预测记录与备份恢复流程。</p>
                      <div className={styles.dataActions}>
                        <button type="button" className={styles.secondaryBtn}>
                          数据备份
                        </button>
                        <button type="button" className={styles.secondaryBtn}>
                          数据恢复
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <h3>账户数据</h3>
                      <p>导出或删除个人账户资料。高风险操作仍需管理员权限确认。</p>
                      <div className={styles.dataActions}>
                        <button type="button" className={styles.secondaryBtn}>
                          导出数据
                        </button>
                        <button type="button" className={styles.dangerBtn}>
                          删除账户
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </section>
          ) : null}
        </main>
      </div>

      <OverlayDialog
        open={confirmClearOpen}
        title="确认清除本地数据？"
        description="这会移除当前浏览器中的缓存与临时记录，操作后无法恢复。"
        confirmText="确认清除"
        cancelText="暂不清除"
        tone="danger"
        onCancel={() => setConfirmClearOpen(false)}
        onConfirm={handleConfirmClearData}
      />
    </div>
  );
}
