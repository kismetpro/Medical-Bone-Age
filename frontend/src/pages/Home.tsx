import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Activity, Shield, Users, BarChart3, ArrowRight } from 'lucide-react';
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

                <section className={styles.features}>
                    <motion.div
                        whileHover={{ y: -5 }}
                        className={styles.featureCard}
                    >
                        <div className={styles.iconWrapper} style={{ background: '#eff6ff', color: '#3b82f6' }}>
                            <Activity size={24} />
                        </div>
                        <h3>智能推断</h3>
                        <p>结合基于 ResNet 的预测和 RUS-CHN 分期模型，提供最准确的骨龄评估结果。</p>
                    </motion.div>

                    <motion.div
                        whileHover={{ y: -5 }}
                        className={styles.featureCard}
                    >
                        <div className={styles.iconWrapper} style={{ background: '#f0fdf4', color: '#22c55e' }}>
                            <Users size={24} />
                        </div>
                        <h3>成长追踪</h3>
                        <p>清晰的历史时间线和生长曲线，轻松掌握孩子的近远期发育轨迹。</p>
                    </motion.div>

                    <motion.div
                        whileHover={{ y: -5 }}
                        className={styles.featureCard}
                    >
                        <div className={styles.iconWrapper} style={{ background: '#fef2f2', color: '#ef4444' }}>
                            <Shield size={24} />
                        </div>
                        <h3>医生验证</h3>
                        <p>基于 Grad-CAM 与特征异常检测，显著帮助临床医生做出准确决策。</p>
                    </motion.div>

                    <motion.div
                        whileHover={{ y: -5 }}
                        className={styles.featureCard}
                    >
                        <div className={styles.iconWrapper} style={{ background: '#f5f3ff', color: '#8b5cf6' }}>
                            <BarChart3 size={24} />
                        </div>
                        <h3>综合报告</h3>
                        <p>一键自动生成专业的体检与骨龄发育报告，可一键打印和分享。</p>
                    </motion.div>
                </section>
            </main>
        </div>
    );
}
