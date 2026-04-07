import { Link } from 'react-router-dom';
import { Activity, ArrowRight, ChevronDown, ChevronUp, Settings } from 'lucide-react';
import { type CSSProperties, useEffect, useRef, useState } from 'react';
import CookieSettings from '../components/CookieSettings';
import styles from './Home.module.css';

const platformPills = ['骨龄预测', '小关节分级', 'AI 助手', '问答社区'];

const heroMetrics = [
  { value: 'ResNet50', label: '多模型骨龄回归' },
  { value: '±5° TTA', label: '旋转增强稳定输出' },
  { value: 'GradCAM', label: '热力图可解释分析' },
];

const showcaseSections = [
  {
    title: '把一次上传，变成稳定可复现的骨龄判断',
    description:
      '从影像进入系统的那一刻起，流程就不再依赖运气。平台会先完成图像校验，再按需执行亮度与对比度增强，把原始影像送入融合性别信息的 ResNet50 骨龄回归模型，并叠加 ±5° Test-Time Augmentation 与多模型集成，将输出统一回映到月龄区间，让一次上传也能获得更稳、更一致、更可复现的骨龄结论。',
    eyebrow: 'Bone Age Prediction I',
    reverse: false,
    visualLabel: 'Prediction Pipeline',
    chips: ['图像校验', '亮度 / 对比度预处理', '性别特征融合', '分段集成回归'],
    features: [
      {
        title: '输入先做稳态处理',
        text: '上传影像会先经过内容校验，必要时应用 brightness / contrast 预处理，把低对比片也尽量拉回稳定推理分布。',
      },
      {
        title: '多模型联合回归',
        text: '骨龄主模型以 ResNet50 为骨干，输出归一化年龄，再按各模型覆盖范围回映到真实月龄并做平均，降低单模型偏移。',
      },
      {
        title: 'TTA 让结果更稳',
        text: '同一张影像会额外做 -5° 与 +5° 旋转推理，缓解轻微摆位差异，让预测在临床上传场景里更有韧性。',
      },
    ],
  },
  {
    title: '给出的不只是骨龄，而是一整页可追问的医学上下文',
    description:
      '真正能落地的系统，从来不只输出一个数字。骨龄预测完成后，后端会并行补齐异常与异物筛查、小关节识别、RUS 语义整理与 GradCAM 热力图解释；如果同时提供身高，平台还会结合成长标准估算成年身高。最终呈现的不是孤立年龄值，而是一份可以解释、可以复核、可以继续追踪的完整医学上下文。',
    eyebrow: 'Bone Age Prediction II',
    reverse: true,
    visualLabel: 'Clinical Context',
    chips: ['异物 / 骨折提醒', 'GradCAM 热力图', 'RUS-CHN 细项', '成年身高估计'],
    features: [
      {
        title: '异常线索同步筛查',
        text: '预测接口会并行执行异常检测，并将高风险异物或骨折线索作为提醒返回，避免影像质量与伪影直接污染最终判断。',
      },
      {
        title: '热力图辅助解释',
        text: 'GradCAM 会把骨龄模型最关注的结构可视化，帮助医生快速理解模型是关注腕部、骨骺还是某些关键骨化中心。',
      },
      {
        title: '报告从骨龄延伸到成长',
        text: '系统会拼装 RUS-CHN 细项说明，并在提供身高时用成长标准估计成年身高，让结果更接近临床沟通语境。',
      },
    ],
  },
  {
    title: '先把每一个关键骨点找准，分级才真正成立',
    description:
      '小关节分级不是整图猜测，而是对关键结构的逐点确认。系统会先定位 RUS 13 点并自动判断左右手，再把检测结果统一标准化为 Radius、Ulna、MCP、PIP、DIP 等语义关节。接口还支持 DP V3 增强模式，让 YOLO 检测、灰度区域扩展与去重合并协同工作，把“先找准位置”这件事做得更完整、更扎实。',
    eyebrow: 'Joint Grading I',
    reverse: false,
    visualLabel: 'Joint Detection',
    chips: ['YOLO 基础检测', 'DP V3 增强', '手性自动判定', 'RUS 13 点标准化'],
    features: [
      {
        title: 'YOLO 负责抓住主骨点',
        text: '基础流程会先锁定主要小关节框，并生成可视化叠图，让医生能直观看到系统到底找到了哪些关键结构。',
      },
      {
        title: 'DP V3 补足难点区域',
        text: '增强模式会结合 BFS 聚类、灰度扩展与 Union-Find 去重，尝试补足腕部或重叠区域里 YOLO 容易漏掉的骨块。',
      },
      {
        title: '检测结果直接进入标准语义',
        text: '检测到的关节会按左右手顺序和 RUS 13 点命名重新整理，后续分级、评分与报告都建立在同一套标准坐标系之上。',
      },
    ],
  },
  {
    title: '让每个关节各司其职，最后汇成一套 RUS 结论',
    description:
      '当位置被确认，系统才开始真正的分级。每个检测框都会被裁成 ROI，外扩、缩放到 224×224，并按训练分布完成归一化，再送入对应的小关节专属模型。DIP、PIP、MCP、MIP、Ulna、Radius 分别拥有独立权重映射，之后再统一完成语义对齐与 RUS-CHN 公式折算，把离散等级整合成一套可用于临床复核的总分体系。',
    eyebrow: 'Joint Grading II',
    reverse: true,
    visualLabel: 'RUS Scoring',
    chips: ['ROI 外扩裁剪', '224×224 归一化', '专属关节权重', 'RUS-CHN 折算'],
    features: [
      {
        title: '专属模型分别负责不同骨点',
        text: 'DIP、PIP、MCP、MIP、Ulna、Radius 分别映射到对应权重，避免用同一套分类边界粗暴覆盖不同成熟节律的关节。',
      },
      {
        title: '推理过程与训练严格对齐',
        text: '分级时沿用训练阶段的 RGB 输入、224 尺寸与 ImageNet 归一化，尽量保证线上推理与离线训练保持同分布。',
      },
      {
        title: '等级最终回到 RUS 体系',
        text: '关节原始 grade_raw 会被重新语义对齐，再累积成 RUS 总分与细项详情，为公式法骨龄换算与人工复核同时服务。',
      },
    ],
  },
  {
    title: '同一套 AI 底座，同时服务患者沟通与医生决策',
    description:
      '智能问诊不只是一个聊天框，而是一套按角色切换的医学沟通接口。患者端采用更易懂、更温和的健康科普提示词，并支持直接上传影像进行多模态问诊；医生端则切换为更谨慎、结构化的辅助诊断模式，还能附带 prediction_id 与额外上下文，把病例信息一并送入模型。相同的流式体验，服务的是两种完全不同的专业场景。',
    eyebrow: 'AI Assistant',
    reverse: false,
    visualLabel: 'Role-Aware Copilot',
    chips: ['DeepSeek', '流式输出', '图像问诊', '病例上下文注入'],
    features: [
      {
        title: '患者模式更注重解释',
        text: '系统会引导模型用通俗语言回答骨龄、生长发育与就医建议，帮助家长先建立正确认知，再去做线下决策。',
      },
      {
        title: '医生模式更注重结构化',
        text: '医生助手支持附带预测记录和额外上下文，让 AI 生成更偏临床沟通、报告整理与诊疗建议草稿的内容。',
      },
      {
        title: '文字与图片都能进入会话',
        text: '患者上传 X 光片时，会走图文一体的请求格式；同时所有回答都以流式方式返回，减少等待并保留对话的实时感。',
      },
    ],
  },
];

const matrixCards = [
  {
    title: '专家科普文章',
    description: '医生可以直接在平台发布骨龄、营养、长高与发育管理相关文章，把零散经验沉淀成一套持续更新、随时复用的知识资产。',
    eyebrow: 'Articles',
    points: [
      '文章写入后端数据库并按时间倒序展示，首页之外也能在社区页持续更新。',
      '患者先读懂基础概念，再进入预测、问诊与复诊，减少重复解释成本。',
      '医生端与患者端共用同一内容池，让健康教育成为平台的长期资产。',
    ],
  },
  {
    title: '影像问答论坛',
    description: '患者可以携带影像提交问题，医生在同一条目下展开查看、回复与修改，让每一次问诊都留下完整上下文与清晰回路。',
    eyebrow: 'Q&A Workflow',
    points: [
      '问题、影像、回复与更新时间都会落库，普通用户能删除自己的提问，医生能持续跟进同一问题。',
      '前端支持刷新、展开、附件预览与状态标记，把交流从一次性消息升级为结构化答疑。',
      '知识内容与真实问答并存，让平台既能沉淀标准答案，也能承接个体化病例沟通。',
    ],
  },
];

const slideLabels = ['首页', '骨龄预测引擎', ...showcaseSections.map((section) => section.title), '问答社区'];

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

      <div className={styles.slideTopRail} aria-hidden={activeSection === 0}>
        <button
          type="button"
          className={`${styles.slideTopButton} ${activeSection > 0 ? styles.slideTopButtonVisible : ''}`}
          onClick={() => goToSection(0)}
          aria-label="回到第一页"
          tabIndex={activeSection > 0 ? 0 : -1}
        >
          <ChevronUp size={16} />
        </button>
      </div>

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
                    将骨龄预测、小关节分级、AI 问诊与问答社区整合进同一套平台入口，在患者、医生与算法之间建立一条真正能持续运转的临床协作闭环。
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
                <p className={styles.sectionEyebrow}>Bone Age Prediction Engine</p>
                <h2 className={styles.reportHeroTitle}>
                  把骨龄预测
                  <br />
                  <span className={styles.highlight}>做成可交付的临床引擎</span>
                </h2>
                <p className={styles.reportHeroSubtitle}>
                  后端 `/predict` 从来不是单点功能。它把图像校验、可选预处理、多模型集成回归、热力图解释、异常提醒与成长推算串成一条连续工作流，让平台第一项能力就能直接对接真实场景中的“上传、判断、解释、沟通”全流程。
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
                    <div className={`${styles.glassFrame} ${styles.featureVisual}`}>
                      <div className={styles.featureVisualTop}>
                        <span className={styles.featureVisualLabel}>{section.visualLabel}</span>
                        <span className={styles.featureVisualCount}>{section.features.length} 个关键环节</span>
                      </div>

                      <div className={styles.featureList}>
                        {section.features.map((feature, featureIndex) => (
                          <article key={feature.title} className={styles.featureItem}>
                            <span className={styles.featureIndex}>
                              {String(featureIndex + 1).padStart(2, '0')}
                            </span>
                            <div className={styles.featureBody}>
                              <h3 className={styles.featureTitle}>{feature.title}</h3>
                              <p className={styles.featureText}>{feature.text}</p>
                            </div>
                          </article>
                        ))}
                      </div>

                      <div className={styles.featureChipRow}>
                        {section.chips.map((chip) => (
                          <span key={chip} className={styles.featureChip}>
                            {chip}
                          </span>
                        ))}
                      </div>
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
                <p className={styles.sectionEyebrow}>Knowledge & Collaboration</p>
                <h2 className={styles.sectionTitle}>让知识沉淀与病例沟通，一起留在平台里</h2>
                <p className={styles.sectionText}>
                  最后一屏不再停留在离线图表，而是把平台真正在线运转的内容生态完整亮出来。科普文章负责建立认知底盘，问答论坛负责沉淀影像化咨询与医生回复，让“预测之后怎么办”这件事，也拥有持续入口。
                </p>
              </div>

              <div className={styles.matrixGrid}>
                {matrixCards.map((card, index) => (
                  <article
                    key={card.title}
                    className={`${styles.matrixCard} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
                    style={{ transitionDelay: matrixActive ? `${200 + index * 120}ms` : '0ms' }}
                  >
                    <p className={styles.communityEyebrow}>{card.eyebrow}</p>
                    <h3 className={styles.matrixTitle}>{card.title}</h3>
                    <p className={styles.matrixDescription}>{card.description}</p>
                    <div className={styles.communityPointList}>
                      {card.points.map((point, pointIndex) => (
                        <div key={point} className={styles.communityPoint}>
                          <span className={styles.communityPointIndex}>{pointIndex + 1}</span>
                          <span>{point}</span>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>

              <p
                className={`${styles.sectionFooter} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
                style={{ transitionDelay: matrixActive ? '420ms' : '0ms' }}
              >
                从骨龄评估到分级、问诊与社区沉淀，整个平台围绕同一套骨龄业务闭环持续工作
              </p>
              <div
                className={`${styles.finalCtaWrap} ${styles.slideRevealUp} ${matrixActive ? styles.isActive : ''}`}
                style={{ transitionDelay: matrixActive ? '520ms' : '0ms' }}
              >
                <Link to="/auth" className={styles.primaryCta}>
                  立即体验系统
                  <ArrowRight size={18} />
                </Link>
              </div>
            </div>
          </section>
        </div>
      </main>

      <CookieSettings isOpen={showCookieSettings} onClose={() => setShowCookieSettings(false)} />
    </div>
  );
}
