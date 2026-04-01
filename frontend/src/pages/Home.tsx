import { Link } from 'react-router-dom';
import { Activity, ArrowRight, ChevronDown, Settings } from 'lucide-react';
import { type CSSProperties, useEffect, useRef, useState } from 'react';
import CookieSettings from '../components/CookieSettings';
import resultsImage from '../static/boneage_yolov8_report/results.png';
import precisionImage from '../static/boneage_yolov8_report/BoxP_curve.png';
import recallImage from '../static/boneage_yolov8_report/BoxR_curve.png';
import f1Image from '../static/boneage_yolov8_report/BoxF1_curve.png';
import confusionImage from '../static/boneage_yolov8_report/confusion_matrix.png';
import normalizedConfusionImage from '../static/boneage_yolov8_report/confusion_matrix_normalized.png';
import styles from './Home.module.css';

const platformPills = ['骨龄预测', '异常检测', '发育追踪', '临床协同'];

const heroMetrics = [
  { value: '99%+', label: 'mAP50' },
  { value: '1.00', label: 'Precision' },
  { value: '1.00', label: 'Recall' },
];

const showcaseSections = [
  {
    title: '极其稳定的非凡表现',
    description:
      '训练损失持续下降，验证集 mAP50 快速逼近 1.00。模型在定位、分类与泛化能力上同步收敛，证明小关节检测模块已经具备稳定的临床级表现。',
    image: resultsImage,
    alt: 'YOLOv8 训练与验证指标',
    eyebrow: 'Training Dynamics',
    reverse: false,
  },
  {
    title: '无懈可击的精度',
    description:
      '在约 0.84 的置信度阈值附近，整体精度达到 1.00。模型几乎只输出真实阳性预测框，能有效降低误报，保障医生对检测结果的信任。',
    image: precisionImage,
    alt: 'Precision-Confidence 曲线',
    eyebrow: 'Precision Curve',
    reverse: true,
  },
  {
    title: '绝不漏掉任何细节',
    description:
      '在较宽的低阈值区间内，召回率长期维持在 1.00。无论是 Radius、Ulna 还是多处重叠小关节，模型都能尽可能完整地捕捉关键解剖结构。',
    image: recallImage,
    alt: 'Recall-Confidence 曲线',
    eyebrow: 'Recall Curve',
    reverse: false,
  },
  {
    title: '精与准的完美平衡',
    description:
      '在约 0.616 的阈值下，F1 得分达到 1.00，意味着模型同时兼顾极低误报与极低漏检，在医疗辅助判读中给出更可靠的综合决策依据。',
    image: f1Image,
    alt: 'F1-Confidence 曲线',
    eyebrow: 'F1 Balance',
    reverse: true,
  },
];

const matrixCards = [
  {
    title: '混淆矩阵',
    description: '绝对数量统计下，主要关节几乎全部沿对角线分布，错误预测寥寥无几。',
    image: confusionImage,
    alt: 'YOLOv8 混淆矩阵',
  },
  {
    title: '归一化混淆矩阵',
    description: '比例归一化后，多数类别保持接近 1.00 的正确识别率，类别区分清晰稳定。',
    image: normalizedConfusionImage,
    alt: 'YOLOv8 归一化混淆矩阵',
  },
];

const slideLabels = ['首页', '项目特性', ...showcaseSections.map((section) => section.title), '混淆矩阵'];

const TRANSITION_LOCK_MS = 950;
const SWIPE_THRESHOLD = 60;
const WHEEL_THRESHOLD = 24;

export default function Home() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [showCookieSettings, setShowCookieSettings] = useState(false);
  const [activeSection, setActiveSection] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(() =>
    typeof window !== 'undefined' ? window.innerHeight : 1
  );

  const activeSectionRef = useRef(0);
  const transitioningRef = useRef(false);
  const touchStartYRef = useRef<number | null>(null);
  const unlockTimeoutRef = useRef<number | null>(null);
  const goToSectionRef = useRef<(targetIndex: number) => void>(() => {});

  const totalSlides = slideLabels.length;
  const safeViewportHeight = Math.max(viewportHeight, 1);
  const viewportStyle = {
    '--slide-height': `${safeViewportHeight}px`,
    '--active-section': activeSection,
    '--slide-count': totalSlides,
  } as CSSProperties;

  const goToSection = (targetIndex: number) => {
    if (showCookieSettings) {
      return;
    }

    const boundedIndex = Math.max(0, Math.min(totalSlides - 1, targetIndex));
    if (boundedIndex === activeSectionRef.current || transitioningRef.current) {
      return;
    }

    transitioningRef.current = true;
    activeSectionRef.current = boundedIndex;
    setActiveSection(boundedIndex);

    if (unlockTimeoutRef.current !== null) {
      window.clearTimeout(unlockTimeoutRef.current);
    }

    unlockTimeoutRef.current = window.setTimeout(() => {
      transitioningRef.current = false;
    }, TRANSITION_LOCK_MS);
  };

  goToSectionRef.current = goToSection;

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      const x = (event.clientX / window.innerWidth - 0.5) * 18;
      const y = (event.clientY / window.innerHeight - 0.5) * 18;
      setMousePosition({ x, y });
    };

    const handleResize = () => {
      setViewportHeight(window.innerHeight);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    activeSectionRef.current = activeSection;
  }, [activeSection]);

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const previousHtmlOverflow = html.style.overflow;
    const previousBodyOverflow = body.style.overflow;
    const previousBodyOverscroll = body.style.overscrollBehavior;

    window.scrollTo(0, 0);
    html.style.overflow = 'hidden';
    body.style.overflow = 'hidden';
    body.style.overscrollBehavior = 'none';

    return () => {
      html.style.overflow = previousHtmlOverflow;
      body.style.overflow = previousBodyOverflow;
      body.style.overscrollBehavior = previousBodyOverscroll;
    };
  }, []);

  useEffect(() => {
    const stepSection = (direction: 1 | -1) => {
      goToSectionRef.current(activeSectionRef.current + direction);
    };

    const handleWheel = (event: WheelEvent) => {
      if (showCookieSettings) {
        return;
      }

      event.preventDefault();
      if (Math.abs(event.deltaY) < WHEEL_THRESHOLD) {
        return;
      }

      stepSection(event.deltaY > 0 ? 1 : -1);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (showCookieSettings) {
        return;
      }

      if (event.key === 'ArrowDown' || event.key === 'PageDown') {
        event.preventDefault();
        stepSection(1);
      } else if (event.key === 'ArrowUp' || event.key === 'PageUp') {
        event.preventDefault();
        stepSection(-1);
      } else if (event.key === 'Home') {
        event.preventDefault();
        goToSectionRef.current(0);
      } else if (event.key === 'End') {
        event.preventDefault();
        goToSectionRef.current(totalSlides - 1);
      }
    };

    const handleTouchStart = (event: TouchEvent) => {
      if (showCookieSettings) {
        return;
      }

      touchStartYRef.current = event.changedTouches[0]?.clientY ?? null;
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (showCookieSettings) {
        return;
      }

      event.preventDefault();
    };

    const handleTouchEnd = (event: TouchEvent) => {
      if (showCookieSettings) {
        return;
      }

      const touchStart = touchStartYRef.current;
      const touchEnd = event.changedTouches[0]?.clientY ?? null;
      touchStartYRef.current = null;

      if (touchStart === null || touchEnd === null) {
        return;
      }

      const difference = touchStart - touchEnd;
      if (Math.abs(difference) < SWIPE_THRESHOLD) {
        return;
      }

      stepSection(difference > 0 ? 1 : -1);
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('touchstart', handleTouchStart, { passive: false });
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd, { passive: false });

    return () => {
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [showCookieSettings, totalSlides]);

  useEffect(() => {
    return () => {
      if (unlockTimeoutRef.current !== null) {
        window.clearTimeout(unlockTimeoutRef.current);
      }
    };
  }, []);

  const heroActive = activeSection === 0;
  const projectActive = activeSection === 1;
  const matrixSlideIndex = totalSlides - 1;
  const matrixActive = activeSection === matrixSlideIndex;

  return (
    <div className={styles.homeContainer}>
      <div
        className={styles.backgroundParallax}
        style={{
          transform: `translate3d(${mousePosition.x * 0.3}px, ${mousePosition.y * 0.3}px, 0)`,
        }}
      />

      <header className={styles.header}>
        <div className={styles.logo}>
          <div className={styles.logoBadge}>
            <Activity size={20} />
          </div>
          <span>骨龄 AI 平台</span>
        </div>

        <nav className={styles.nav}>
          <Link to="/message" className={styles.navLink}>
            资讯中心
          </Link>
          <Link to="/consultation" className={styles.navLink}>
            智能问诊
          </Link>
          <Link to="/auth" className={styles.loginBtn}>
            登录
          </Link>
          <Link to="/auth" className={styles.registerBtn}>
            免费注册
          </Link>
          <button
            className={styles.settingsButton}
            onClick={() => setShowCookieSettings(true)}
            aria-label="Cookie设置"
          >
            <Settings size={18} />
          </button>
        </nav>
      </header>

      <aside className={styles.slideRail} aria-label="首页板块导航">
        <div className={styles.slideDots}>
          {slideLabels.map((label, index) => (
            <button
              key={label}
              type="button"
              className={`${styles.slideDot} ${index === activeSection ? styles.slideDotActive : ''}`}
              onClick={() => goToSection(index)}
              aria-label={`切换到${label}`}
              aria-current={index === activeSection ? 'true' : 'false'}
            />
          ))}
        </div>
      </aside>

      <main className={styles.viewport} style={viewportStyle}>
        <div className={styles.slidesTrack}>
          <section className={`${styles.slide} ${styles.heroSlide}`}>
            <div className={`${styles.slideShell} ${styles.heroShell}`}>
              <div
                className={styles.heroScene}
                style={{
                  transform: `translate3d(${mousePosition.x * 0.45}px, ${mousePosition.y * 0.45}px, 0)`,
                }}
              >
                <div
                  className={`${styles.heroPanel} ${styles.slideRevealUp} ${heroActive ? styles.isActive : ''}`}
                >
                  <div className={styles.badge}>新一代医疗辅助诊断 AI</div>
                  <h1 className={styles.title}>
                    智能骨龄
                    <br />
                    <span className={styles.highlight}>评估与关节识别平台</span>
                  </h1>
                  <p className={styles.subtitle}>
                    将骨龄预测、异常检测与小关节识别整合为一个统一入口，在患者、医生与模型之间建立更快、更稳、更透明的诊断协作流程。
                  </p>

                  <div className={styles.pillRow}>
                    {platformPills.map((pill, index) => (
                      <span
                        key={pill}
                        className={`${styles.infoPill} ${styles.slideRevealUp} ${heroActive ? styles.isActive : ''}`}
                        style={{ transitionDelay: heroActive ? `${180 + index * 90}ms` : '0ms' }}
                      >
                        {pill}
                      </span>
                    ))}
                  </div>

                  <div
                    className={`${styles.ctaGroup} ${styles.slideRevealUp} ${heroActive ? styles.isActive : ''}`}
                    style={{ transitionDelay: heroActive ? '420ms' : '0ms' }}
                  >
                    <Link to="/auth" className={styles.primaryCta}>
                      立即体验系统
                      <ArrowRight size={18} />
                    </Link>
                  </div>
                </div>
              </div>

              <button type="button" className={styles.scrollCue} onClick={() => goToSection(1)}>
                <span>查看项目特性</span>
                <ChevronDown size={22} />
              </button>
            </div>
          </section>

          <section className={`${styles.slide} ${styles.reportSlide}`}>
            <div className={`${styles.slideShell} ${styles.centeredShell}`}>
              <div
                className={`${styles.reportHeroContent} ${styles.slideRevealUp} ${
                  projectActive ? styles.isActive : ''
                }`}
              >
                <p className={styles.sectionEyebrow}>YOLOv8 Bone-Age Detection Report</p>
                <h2 className={styles.reportHeroTitle}>
                  重新定义精准
                  <br />
                  <span className={styles.highlight}>骨龄关节识别</span>
                </h2>
                <p className={styles.reportHeroSubtitle}>
                  基于 YOLOv8 架构构建的小关节检测能力，为手部骨龄评估提供高速、稳定、可解释的视觉基础。模型在多项关键指标上接近满分，适合承担高强度医学辅助场景中的前置识别任务。
                </p>
              </div>

              <div className={styles.metricsGrid}>
                {heroMetrics.map((metric, index) => (
                  <article
                    key={metric.label}
                    className={`${styles.metricCard} ${styles.slideRevealUp} ${
                      projectActive ? styles.isActive : ''
                    }`}
                    style={{ transitionDelay: projectActive ? `${200 + index * 120}ms` : '0ms' }}
                  >
                    <span className={styles.metricValue}>{metric.value}</span>
                    <span className={styles.metricLabel}>{metric.label}</span>
                  </article>
                ))}
              </div>
            </div>
          </section>

          {showcaseSections.map((section, index) => {
            const slideIndex = index + 2;
            const slideActive = activeSection === slideIndex;
            const contentAnimation = section.reverse ? styles.slideRevealRight : styles.slideRevealLeft;
            const visualAnimation = section.reverse ? styles.slideRevealLeft : styles.slideRevealRight;

            return (
              <section key={section.title} className={`${styles.slide} ${styles.storySlide}`}>
                <div className={`${styles.slideShell} ${styles.storyShell} ${section.reverse ? styles.reverse : ''}`}>
                  <div className={`${styles.storyCopy} ${contentAnimation} ${slideActive ? styles.isActive : ''}`}>
                    <p className={styles.sectionEyebrow}>{section.eyebrow}</p>
                    <h2 className={styles.sectionTitle}>{section.title}</h2>
                    <p className={styles.sectionText}>{section.description}</p>
                  </div>

                  <div
                    className={`${styles.storyVisual} ${visualAnimation} ${slideActive ? styles.isActive : ''}`}
                    style={{ transitionDelay: slideActive ? '120ms' : '0ms' }}
                  >
                    <div className={styles.glassFrame}>
                      <img src={section.image} alt={section.alt} className={styles.glassImage} />
                    </div>
                  </div>
                </div>
              </section>
            );
          })}

          <section className={`${styles.slide} ${styles.matrixSlide}`}>
            <div className={`${styles.slideShell} ${styles.centeredShell}`}>
              <div
                className={`${styles.matrixIntro} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
              >
                <p className={styles.sectionEyebrow}>Confusion Matrix</p>
                <h2 className={styles.sectionTitle}>对每一个关节了如指掌</h2>
                <p className={styles.sectionText}>
                  从绝对数量到归一化比例，混淆矩阵都展示出清晰的类别边界。主要关节如 ProximalPhalanx、MCP 与
                  DistalPhalanx 的分类结果高度集中，背景误识别率接近于零。
                </p>
              </div>

              <div className={styles.matrixGrid}>
                {matrixCards.map((card, index) => (
                  <article
                    key={card.title}
                    className={`${styles.matrixCard} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
                    style={{ transitionDelay: matrixActive ? `${200 + index * 120}ms` : '0ms' }}
                  >
                    <div className={styles.glassFrame}>
                      <img src={card.image} alt={card.alt} className={styles.glassImage} />
                    </div>
                    <h3 className={styles.matrixTitle}>{card.title}</h3>
                    <p className={styles.matrixDescription}>{card.description}</p>
                  </article>
                ))}
              </div>

              <p
                className={`${styles.sectionFooter} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
                style={{ transitionDelay: matrixActive ? '420ms' : '0ms' }}
              >
                基于 YOLOv8 的手部小关节医学预测模型性能展示
              </p>
            </div>
          </section>
        </div>
      </main>

      <CookieSettings isOpen={showCookieSettings} onClose={() => setShowCookieSettings(false)} />
    </div>
  );
}
