import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Activity, ArrowRight } from 'lucide-react';
import styles from './Home.module.css';

export default function Home() {
    return (
        <div className={styles.homeContainer}>
            <header className={styles.header}>
                <div className={styles.logo}>
                    <Activity size={28} color="#3b82f6" />
                    <span>骨龄 AI 平台</span>
                </div>
                <nav className={styles.nav}>
                    <Link to="/auth" className={styles.loginBtn}>登录</Link>
                    <Link to="/auth" className={styles.registerBtn}>免费注册</Link>
                </nav>
            </header>

            <main className={styles.main}>
                <motion.section
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className={styles.heroSection}
                >
                    <div className={styles.badge}>新一代医疗辅助诊断 AI</div>
                    <h1 className={styles.title}>
                        智能骨龄 <br />
                        <span className={styles.highlight}>评估平台</span>
                    </h1>
                    <p className={styles.subtitle}>
                        强大的深度学习系统，连接患者与临床医生。在一个平台上体验即时骨龄预测、异常检测和发育追踪。
                    </p>
                    <div className={styles.ctaGroup}>
                        <Link to="/auth" className={styles.primaryCta}>
                            立即体验系统 <ArrowRight size={18} />
                        </Link>
                    </div>
                </motion.section>

  
            </main>
        </div>
    );
}
