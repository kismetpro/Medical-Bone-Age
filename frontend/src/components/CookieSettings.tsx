import { useState, useEffect } from 'react';
import { X, RefreshCw, Trash2, Check, X as CloseIcon } from 'lucide-react';
import { ConsentCookie, PreferencesCookie } from '../lib/cookieManager';
import styles from './CookieSettings.module.css';

interface CookieSettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CookieSettings({ isOpen, onClose }: CookieSettingsProps) {
  const [preferences, setPreferences] = useState({
    necessary: true,
    functional: true,
    analytics: false
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const savedPrefs = PreferencesCookie.getPreferences();
    if (savedPrefs && Object.keys(savedPrefs).length > 0) {
      setPreferences(savedPrefs);
    }
  }, [isOpen]);

  const handleToggle = (key: keyof typeof preferences) => {
    if (key === 'necessary') return;
    
    const newPrefs = { ...preferences, [key]: !preferences[key] };
    setPreferences(newPrefs);
    setHasChanges(true);
  };

  const handleSave = () => {
    PreferencesCookie.setPreferences(preferences);
    ConsentCookie.setConsent(preferences.functional || preferences.analytics);
    setHasChanges(false);
    onClose();
  };

  const handleReset = () => {
    const defaultPrefs = {
      necessary: true,
      functional: true,
      analytics: false
    };
    setPreferences(defaultPrefs);
    setHasChanges(true);
  };

  const handleClearAll = () => {
    if (confirm('确定要清除所有Cookie吗？这将导致您需要重新登录。')) {
      localStorage.clear();
      sessionStorage.clear();
      document.cookie.split(';').forEach(cookie => {
        const eqPos = cookie.indexOf('=');
        const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
        document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
      });
      window.location.reload();
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.headerContent}>
            <div className={styles.iconWrapper}>
              <RefreshCw size={20} />
            </div>
            <div>
              <h2>Cookie 设置</h2>
              <p>管理您的Cookie偏好</p>
            </div>
          </div>
          <button className={styles.closeButton} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.section}>
            <h3>Cookie 类型</h3>
            <p className={styles.description}>
              选择您希望接受的Cookie类型。您可以随时更改这些设置。
            </p>

            <div className={styles.cookieTypes}>
              <div className={`${styles.cookieType} ${styles.necessary}`}>
                <div className={styles.cookieTypeHeader}>
                  <div className={styles.checkboxWrapper}>
                    <input
                      type="checkbox"
                      id="necessary"
                      checked={preferences.necessary}
                      disabled
                      className={styles.checkbox}
                    />
                    <label htmlFor="necessary" className={styles.checkboxLabel}>
                      <Check size={16} />
                    </label>
                  </div>
                  <div className={styles.cookieTypeInfo}>
                    <h4>必要 Cookie</h4>
                    <p>用于系统基本功能，如用户登录、会话管理等</p>
                  </div>
                  <span className={styles.badge}>必需</span>
                </div>
              </div>

              <div className={`${styles.cookieType} ${preferences.functional ? styles.active : ''}`}>
                <div className={styles.cookieTypeHeader}>
                  <div className={styles.checkboxWrapper}>
                    <input
                      type="checkbox"
                      id="functional"
                      checked={preferences.functional}
                      onChange={() => handleToggle('functional')}
                      className={styles.checkbox}
                    />
                    <label htmlFor="functional" className={styles.checkboxLabel}>
                      {preferences.functional && <Check size={16} />}
                    </label>
                  </div>
                  <div className={styles.cookieTypeInfo}>
                    <h4>功能 Cookie</h4>
                    <p>记住您的界面偏好设置，如主题、语言等</p>
                  </div>
                </div>
              </div>

              <div className={`${styles.cookieType} ${preferences.analytics ? styles.active : ''}`}>
                <div className={styles.cookieTypeHeader}>
                  <div className={styles.checkboxWrapper}>
                    <input
                      type="checkbox"
                      id="analytics"
                      checked={preferences.analytics}
                      onChange={() => handleToggle('analytics')}
                      className={styles.checkbox}
                    />
                    <label htmlFor="analytics" className={styles.checkboxLabel}>
                      {preferences.analytics && <Check size={16} />}
                    </label>
                  </div>
                  <div className={styles.cookieTypeInfo}>
                    <h4>分析 Cookie</h4>
                    <p>帮助我们了解用户使用情况，改进产品体验</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className={styles.section}>
            <h3>Cookie 管理</h3>
            <div className={styles.managementOptions}>
              <button className={styles.resetButton} onClick={handleReset}>
                <RefreshCw size={16} />
                重置为默认设置
              </button>
              <button className={styles.clearButton} onClick={handleClearAll}>
                <Trash2 size={16} />
                清除所有 Cookie
              </button>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button className={styles.cancelButton} onClick={onClose}>
            取消
          </button>
          <button
            className={`${styles.saveButton} ${!hasChanges ? styles.disabled : ''}`}
            onClick={handleSave}
            disabled={!hasChanges}
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}