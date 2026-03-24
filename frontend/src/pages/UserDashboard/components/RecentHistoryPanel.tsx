import styles from '../UserDashboard.module.css';
import type { PredictionResult } from '../types';

interface RecentHistoryPanelProps {
  history: PredictionResult[];
  onSelect: (item: PredictionResult) => void;
}

export default function RecentHistoryPanel({ history, onSelect }: RecentHistoryPanelProps) {
  return (
    <div className={styles.historyPanel}>
      <h4>最近评估</h4>
      <div className={styles.historyList}>
        {history.length > 0 ? (
          history.map((item) => (
            <button
              key={item.id}
              type="button"
              className={styles.historyItem}
              onClick={() => onSelect(item)}
            >
              <div className={styles.historyMeta}>
                <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                <span className={item.gender === 'male' ? styles.tagMale : styles.tagFemale}>
                  {item.gender === 'male' ? '男' : '女'}
                </span>
              </div>
              <div className={styles.historyScore}>
                {item.predicted_age_years.toFixed(1)} 岁
              </div>
            </button>
          ))
        ) : (
          <p className={styles.emptyText}>暂无最近评估记录。</p>
        )}
      </div>
    </div>
  );
}
