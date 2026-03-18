import React from 'react';
import styles from '../DoctorDashboard.module.css';

interface ArticlesTabProps {
    newArticle: { title: string; content: string };
    setNewArticle: React.Dispatch<React.SetStateAction<{ title: string; content: string }>>;
    submitArticle: () => void;
}

const ArticlesTab: React.FC<ArticlesTabProps> = ({ newArticle, setNewArticle, submitArticle }) => {
    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.tableCard} style={{ padding: '2rem' }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>发布科普文章</h3>
                <input 
                    className={styles.formInput} 
                    style={{ marginBottom: '1rem' }} 
                    placeholder="文章标题" 
                    value={newArticle.title} 
                    onChange={(event) => setNewArticle((previous) => ({ ...previous, title: event.target.value }))} 
                />
                <textarea 
                    className={styles.textareaInput} 
                    placeholder="在这里编写文章内容..." 
                    value={newArticle.content} 
                    onChange={(event) => setNewArticle((previous) => ({ ...previous, content: event.target.value }))} 
                />
                <button className={styles.primaryActionBtn} style={{ marginTop: '1rem' }} onClick={() => void submitArticle()}>发布文章</button>
            </div>
        </div>
    );
};

export default ArticlesTab;
