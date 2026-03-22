import { useState, useEffect } from 'react';
import { X, Settings } from 'lucide-react';
import { ConsentCookie } from '../lib/cookieManager';
import styles from './CookieBanner.module.css';

export default function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (!ConsentCookie.hasConsented()) {
      setIsVisible(true);
    }
  }, []);

  const handleAccept = () => {
    ConsentCookie.setConsent(true);
    setIsVisible(false);
  };

  const handleReject = () => {
    ConsentCookie.setConsent(false);
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className={styles.cookiePopup}>
      <div className={styles.cookieIcon}>
        <svg 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ fontSize: '80px' }}
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a10 10 0 0 1 10 10" />
          <circle cx="12" cy="12" r="3" />
          <path d="M12 15v6" />
          <path d="M12 3v3" />
          <path d="M21 12h-3" />
          <path d="M6 12H3" />
          <path d="M18.36 18.36l-2.12-2.12" />
          <path d="M7.76 7.76L5.64 5.64" />
          <path d="M18.36 5.64l-2.12 2.12" />
          <path d="M7.76 16.24l-2.12 2.12" />
        </svg>
      </div>

      <p className={styles.cookieText}>
        本网站使用 Cookie 来确保您在我们的网站上获得最佳体验。
      </p>

      <div className={styles.buttonContainer}>
        <button 
          className={styles.cookieButton}
          onClick={handleAccept}
        >
          接受所有 Cookie
        </button>
        <button 
          className={styles.cookieButton}
          onClick={handleReject}
        >
          仅必要 Cookie
        </button>
      </div>

      <button 
        className={styles.customizeButton}
        onClick={() => setShowDetails(!showDetails)}
      >
        {showDetails ? '收起设置' : '自定义设置'}
      </button>

      {showDetails && (
        <div className={styles.detailsPanel}>
          <div className={styles.detailSection}>
            <strong>必要 Cookie：</strong>
            <p>用于系统基本功能，如用户登录、会话管理等。这些 Cookie 是必需的，无法禁用。</p>
          </div>
          <div className={styles.detailSection}>
            <strong>功能 Cookie：</strong>
            <p>记住您的界面偏好设置，如主题、语言等。这些 Cookie 可以选择禁用。</p>
          </div>
          <div className={styles.detailSection}>
            <strong>分析 Cookie：</strong>
            <p>帮助我们了解用户使用情况，改进产品体验。这些 Cookie 可以选择禁用。</p>
          </div>
        </div>
      )}
    </div>
  );
}