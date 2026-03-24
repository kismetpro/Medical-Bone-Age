import type { ReactNode } from 'react';
import styles from './OverlayDialog.module.css';

interface OverlayDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  tone?: 'primary' | 'danger';
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
}

export default function OverlayDialog({
  open,
  title,
  description,
  confirmText = '确认',
  cancelText = '取消',
  tone = 'primary',
  onConfirm,
  onCancel,
  children,
}: OverlayDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className={styles.backdrop} onClick={onCancel} role="presentation">
      <div
        className={styles.dialog}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="overlay-dialog-title"
      >
        <div className={styles.header}>
          <h3 id="overlay-dialog-title">{title}</h3>
          {description ? <p>{description}</p> : null}
        </div>

        {children ? <div className={styles.content}>{children}</div> : null}

        <div className={styles.actions}>
          <button type="button" className={styles.cancelButton} onClick={onCancel}>
            {cancelText}
          </button>
          <button
            type="button"
            className={tone === 'danger' ? styles.dangerButton : styles.confirmButton}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
