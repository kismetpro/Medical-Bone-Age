import React, { useState, useEffect, useRef } from 'react';
import styles from './Message.module.css'; // 建议创建对应的 CSS 模块文件

// 定义文章数据类型
interface Article {
  title: string;
  date: string;
  content: string;
}

interface ArticleItem {
  id: string;
  title: string;
  date: string;
  desc: string;
  imgSrc: string;
}

interface CarouselItem {
  id: string;
  imgSrc: string;
  caption: string;
}

interface CardItem {
  id: string;
  text: string;
  bgColor: string;
}

interface TopicItem {
  id: string;
  imgSrc: string;
  text: string;
}

const MessagePage: React.FC = () => {
  // 轮播相关状态
  const [currentSlide, setCurrentSlide] = useState<number>(0);
  // 页面显示状态：list - 列表页，detail - 详情页
  const [pageState, setPageState] = useState<'list' | 'detail'>('list');
  // 当前选中的文章ID
  const [selectedArticleId, setSelectedArticleId] = useState<string>('');
  
  const carouselInnerRef = useRef<HTMLDivElement>(null);

  // 轮播数据
  const carouselItems: CarouselItem[] = [
    {
      id: 'carousel1',
      imgSrc: 'https://picsum.photos/1200/350?random=1',
      caption: '友谊医院微创新技术造福腰椎间盘突出症患者'
    },
    {
      id: 'carousel2',
      imgSrc: 'https://picsum.photos/1200/350?random=2',
      caption: '肌少症与骨质疏松联合防治科普'
    },
    {
      id: 'carousel3',
      imgSrc: 'https://picsum.photos/1200/350?random=3',
      caption: '世界骨质疏松日主题科普'
    }
  ];

  // 右侧快捷卡片数据
  const cardItems: CardItem[] = [
    { id: 'card1', text: '为什么总是膝盖疼痛？这些病因很常见...', bgColor: '#a5c482' },
    { id: 'card2', text: '别再抱怨为什么容易崴脚，你了解...', bgColor: '#73a873' },
    { id: 'card3', text: '地诺单抗对去势肾移植受者小梁骨的...', bgColor: '#e08e6d' },
    { id: 'card4', text: '唑来膦酸钠在绝经后骨质疏松女性中...', bgColor: '#64bcd4' },
    { id: 'card5', text: '专家共识：糖尿病患者骨折风险的管...', bgColor: '#c87a90' },
    { id: 'card6', text: '不用吃射线，超声就能诊断新生儿锁...', bgColor: '#9292cb' }
  ];

  // 文章列表数据
  const articleList: ArticleItem[] = [
    {
      id: 'art1',
      title: '肌少症患者发生骨质疏松的风险是正常人的...',
      date: '2025-12-08',
      desc: '"瓶盖拧不开、买菜拎不动、出门走不快……出现这些情况不全是因为‘年老力衰’，要警惕肌少症与骨质疏松‘狼狈为奸’。" 骨质疏松患者中肌少...',
      imgSrc: 'https://picsum.photos/150/100?random=4'
    },
    {
      id: 'art2',
      title: '世界骨质疏松日中国主题发布：健康体重 强...',
      date: '2025-10-20',
      desc: '10月20日为世界骨质疏松日，中华医学会骨质疏松和骨矿盐疾病分会、中华预防医学会健康传播分会结合我国骨质疏松症防控现状，共同发布今年世界...',
      imgSrc: 'https://picsum.photos/150/100?random=5'
    },
    {
      id: 'art3',
      title: '她咳嗽为何会“咳”断三根肋骨',
      date: '2024-06-14',
      desc: '近日，66岁的张阿姨因咳嗽导致胸部很疼，于是来到“家门口”的上海市静安区市北医院检查，一拍片子，把医生吓了一跳，原来三根肋骨已被“咳”断...',
      imgSrc: 'https://picsum.photos/150/100?random=6'
    }
  ];

  // 右侧专题数据
  const topicItems: TopicItem[] = [
    {
      id: 'topic1',
      imgSrc: 'https://picsum.photos/280/30?random=8',
      text: '外科编译新闻月汇总_...'
    },
    {
      id: 'topic2',
      imgSrc: 'https://picsum.photos/280/30?random=9',
      text: '椎间盘突出大盘点'
    }
  ];

  // 完整文章数据
  const articles: Record<string, Article> = {
    'carousel1': {
      title: '友谊医院微创新技术造福腰椎间盘突出症患者',
      date: '2025-01-15',
      content: `
        <p>近日，友谊医院骨科团队成功开展了经皮内镜下腰椎间盘切除术（PELD）这一微创新技术，为多名重度腰椎间盘突出症患者解除了病痛。该技术通过仅0.8cm的皮肤切口，在高清内镜直视下精准定位突出的髓核组织，在完全不损伤周围神经根和硬膜囊的前提下，完成病变髓核的摘除与神经根减压。</p>
        <p>与传统开放手术相比，该微创手术具有创伤小、出血少、恢复快等显著优势：患者术后24小时即可下床活动，住院时间缩短至3-5天，术后腰腿痛缓解率超过90%。目前已有近百名患者接受该手术，临床随访结果显示复发率低于5%，显著优于传统手术方案。</p>
      `
    },
    'carousel2': {
      title: '肌少症与骨质疏松联合防治科普',
      date: '2025-03-10',
      content: `
        <p>肌少症与骨质疏松被称为“骨骼肌肉的孪生疾病”，二者常常相伴发生，形成恶性循环。研究显示，肌少症患者发生骨质疏松的风险是健康人群的2-3倍，而骨质疏松患者中肌少症的患病率也高达30%-50%。</p>
        <p>肌肉量减少会直接降低对骨骼的力学刺激，加速骨量流失；而骨质疏松导致的骨骼强度下降又会增加跌倒风险，进一步加剧肌肉萎缩。专家建议，中老年人应通过“营养+运动+监测”的综合方案进行防治：每日保证足量优质蛋白摄入，坚持抗阻运动与负重运动，定期检测骨密度与肌肉量，实现早预防、早干预。</p>
      `
    },
    'carousel3': {
      title: '世界骨质疏松日中国主题发布：健康体重 强健骨骼',
      date: '2025-10-20',
      content: `
        <p>10月20日为世界骨质疏松日，中华医学会骨质疏松和骨矿盐疾病分会、中华预防医学会健康传播分会联合发布2025年世界骨质疏松日中国主题：“健康体重 强健骨骼”。</p>
        <p>专家指出，体重过轻会导致骨量峰值不足，而肥胖则会通过炎症反应和机械负荷异常加速骨流失，均会显著增加骨质疏松风险。维持BMI在18.5-23.9之间的健康体重，是保护骨骼健康的重要前提。同时，应注重钙与维生素D的补充，坚持每周3次以上的负重运动，40岁以上人群应定期进行骨密度检测，实现骨质疏松的早诊断、早治疗。</p>
      `
    },
    'card1': {
      title: '为什么总是膝盖疼痛？这些病因很常见',
      date: '2025-02-20',
      content: `
        <p>膝盖疼痛是中老年人最常见的骨骼肌肉问题，其病因复杂多样，常见的包括骨关节炎、半月板损伤、滑膜炎、髌骨软化症等。其中，骨关节炎是导致慢性膝痛的首要原因，患病率随年龄增长显著上升，60岁以上人群患病率超过50%。</p>
        <p>不同病因的膝痛表现各有特点：骨关节炎多表现为活动后加重、休息后缓解的钝痛；半月板损伤常伴随关节弹响与交锁症状；滑膜炎则以关节肿胀、发热为主要表现。专家建议，出现持续膝痛时应及时就医，通过X线、MRI等检查明确病因，避免盲目服用止痛药延误治疗。</p>
      `
    },
    'card2': {
      title: '别再抱怨为什么容易崴脚，你了解踝关节不稳吗？',
      date: '2025-01-25',
      content: `
        <p>反复崴脚并非“运气不好”，而是慢性踝关节不稳的典型表现。据统计，约40%的急性踝关节扭伤患者会发展为慢性不稳，表现为踝关节反复扭伤、行走时“发软”、对不平路面产生恐惧等。</p>
        <p>慢性踝关节不稳的核心原因是韧带损伤后未得到及时修复，导致踝关节机械稳定性下降，同时伴随本体感觉与肌肉力量的减退。治疗上应采取“保守+康复”的综合方案：急性期需制动休息，恢复期通过平衡训练、肌力训练等康复手段恢复踝关节功能，严重病例可考虑韧带重建手术。</p>
      `
    },
    'card3': {
      title: '地诺单抗对去势肾移植受者小梁骨的影响研究',
      date: '2025-04-05',
      content: `
        <p>肾移植受者因长期使用免疫抑制剂，是骨质疏松和骨折的高危人群。最新发表于《Kidney International》的研究显示，地诺单抗可显著改善去势肾移植受者的小梁骨微结构，提升骨密度，且安全性良好。</p>
        <p>该研究纳入120名接受肾移植超过1年的去势男性患者，随机分为地诺单抗组与安慰剂组，随访24个月后，地诺单抗组腰椎骨密度提升8.2%，股骨颈骨密度提升5.1%，小梁骨厚度与数量均显著增加，且未增加感染或肾功能恶化风险。研究提示，地诺单抗可作为肾移植受者骨质疏松治疗的有效选择。</p>
      `
    },
    'card4': {
      title: '唑来膦酸钠在绝经后骨质疏松女性中的长期疗效与安全性',
      date: '2025-03-18',
      content: `
        <p>唑来膦酸钠是一种长效双膦酸盐类药物，每年静脉输注一次即可有效治疗绝经后骨质疏松症。发表于《New England Journal of Medicine》的10年随访研究显示，唑来膦酸钠可显著降低椎体、髋部等部位的骨折风险，且长期使用安全性良好。</p>
        <p>研究结果显示，与安慰剂组相比，唑来膦酸钠组椎体骨折风险降低70%，髋部骨折风险降低41%，且未增加下颌骨坏死或非典型股骨骨折等严重不良事件的发生率。专家建议，绝经后骨质疏松女性可在医生指导下选择唑来膦酸钠进行长期治疗，提升治疗依从性。</p>
      `
    },
    'card5': {
      title: '专家共识：糖尿病患者骨折风险的管理策略',
      date: '2025-02-10',
      content: `
        <p>中华医学会骨质疏松和骨矿盐疾病分会联合内分泌学分会发布《糖尿病患者骨折风险管理专家共识》，明确糖尿病患者骨折风险显著高于非糖尿病人群，且骨折后预后更差。</p>
        <p>共识指出，糖尿病患者骨折风险升高的核心机制包括高糖毒性导致骨质量下降、神经病变与外周血管病变增加跌倒风险、降糖药物对骨骼的潜在影响等。管理策略应涵盖：定期进行骨密度检测与跌倒风险评估，优先选择对骨骼影响较小的降糖药物，必要时启动抗骨质疏松治疗，同时加强跌倒预防与康复干预。</p>
      `
    },
    'card6': {
      title: '不用吃射线，超声就能诊断新生儿锁骨骨折',
      date: '2025-01-30',
      content: `
        <p>新生儿锁骨骨折是产伤性骨折中最常见的类型，传统诊断依赖X线检查，但存在电离辐射风险。最新研究证实，高频超声可作为新生儿锁骨骨折的首选诊断方法，具有无辐射、分辨率高、可实时动态观察等优势。</p>
        <p>超声检查可清晰显示锁骨骨折的部位、类型与移位程度，同时能观察骨痂形成与愈合过程，对新生儿的生长发育无任何不良影响。研究显示，超声诊断新生儿锁骨骨折的准确率超过95%，显著优于临床触诊，可有效避免X线辐射暴露。</p>
      `
    },
    'art1': {
      title: '肌少症患者发生骨质疏松的风险是正常人的2-3倍',
      date: '2025-12-08',
      content: `
        <p>"瓶盖拧不开、买菜拎不动、出门走不快……出现这些情况不全是因为‘年老力衰’，要警惕肌少症与骨质疏松‘狼狈为奸’。" 专家指出，肌少症与骨质疏松常常相伴发生，肌少症患者发生骨质疏松的风险是健康人群的2-3倍。</p>
        <p>肌少症会导致肌肉量减少、力量下降，进而影响骨骼的力学刺激，加速骨量流失；而骨质疏松又会进一步增加跌倒和骨折的风险，形成恶性循环。因此，中老年人应同时关注肌肉和骨骼健康，通过合理营养、规律运动等方式进行综合防治。</p>
      `
    },
    'art2': {
      title: '世界骨质疏松日中国主题发布：健康体重 强健骨骼',
      date: '2025-10-20',
      content: `
        <p>10月20日为世界骨质疏松日，中华医学会骨质疏松和骨矿盐疾病分会、中华预防医学会健康传播分会结合我国骨质疏松症防控现状，共同发布今年世界骨质疏松日中国主题：“健康体重 强健骨骼”。</p>
        <p>专家呼吁，体重过轻或过重都会增加骨质疏松风险，维持健康体重是保护骨骼健康的重要前提。同时，应注重钙和维生素D的摄入，坚持规律的负重运动，定期进行骨密度检测，做到早预防、早诊断、早治疗。</p>
      `
    },
    'art3': {
      title: '她咳嗽为何会“咳”断三根肋骨？警惕骨质疏松性骨折',
      date: '2024-06-14',
      content: `
        <p>近日，66岁的张阿姨因剧烈咳嗽导致胸部剧痛，到医院检查后发现竟“咳”断了三根肋骨。医生介绍，张阿姨患有严重的骨质疏松，骨骼强度大幅下降，轻微的外力（如咳嗽、打喷嚏）都可能引发骨折。</p>
        <p>骨质疏松性骨折多见于中老年人，尤以胸腰椎、髋部和肋骨为高发部位。这类骨折往往预后较差，严重影响患者生活质量，甚至危及生命。因此，中老年人应重视骨质疏松的筛查与干预，避免此类悲剧发生。</p>
      `
    }
  };

  // 轮播更新逻辑
  useEffect(() => {
    if (carouselInnerRef.current) {
      carouselInnerRef.current.style.transform = `translateX(-${currentSlide * 100}%)`;
    }

    // 自动轮播
    const interval = setInterval(() => {
      setCurrentSlide(prev => (prev + 1) % carouselItems.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [currentSlide, carouselItems.length]);

  // 轮播控制方法
  const nextSlide = () => {
    setCurrentSlide(prev => (prev + 1) % carouselItems.length);
  };

  const prevSlide = () => {
    setCurrentSlide(prev => (prev - 1 + carouselItems.length) % carouselItems.length);
  };

  const goToSlide = (index: number) => {
    setCurrentSlide(index);
  };

  // 文章详情页控制方法
  const openArticle = (id: string) => {
    setSelectedArticleId(id);
    setPageState('detail');
  };

  const backToList = () => {
    setPageState('list');
  };

  return (
    <div className={styles.container}>
      {/* 顶部绿色条带 */}
      <div className={styles.topGreenBar}></div>

      {/* 轮播+右侧卡片 - 仅列表页显示 */}
      {pageState === 'list' && (
        <div className={styles.carousel}>
          <div ref={carouselInnerRef} className={styles.carouselInner}>
            {carouselItems.map((item, index) => (
              <div 
                key={item.id} 
                className={`${styles.carouselItem} ${index === currentSlide ? styles.active : ''}`}
                onClick={() => openArticle(item.id)}
              >
                <img src={item.imgSrc} alt={item.caption} />
                <div className={styles.carouselCaption}>{item.caption}</div>
              </div>
            ))}
          </div>

          {/* 右侧快捷卡片区 */}
          <div className={styles.carouselRight}>
            {cardItems.map(item => (
              <div 
                key={item.id} 
                className={styles.card}
                style={{ backgroundColor: item.bgColor }}
                onClick={() => openArticle(item.id)}
              >
                {item.text}
              </div>
            ))}
          </div>

          {/* 轮播控制按钮 */}
          <div className={styles.carouselControls}>
            <button onClick={prevSlide}>&lt;</button>
            <button onClick={nextSlide}>&gt;</button>
          </div>

          {/* 轮播指示器 */}
          <div className={styles.carouselIndicators}>
            {carouselItems.map((_, index) => (
              <span 
                key={index}
                className={`${index === currentSlide ? styles.active : ''}`}
                onClick={() => goToSlide(index)}
              ></span>
            ))}
          </div>
        </div>
      )}

      {/* 主内容区 */}
      {pageState === 'list' ? (
        // 列表页
        <div className={styles.mainContainer}>
          {/* 中间文章列表 */}
          <div className={styles.content}>
            {articleList.map(item => (
              <div 
                key={item.id} 
                className={styles.article}
                onClick={() => openArticle(item.id)}
              >
                <img src={item.imgSrc} alt={item.title} />
                <div className={styles.articleInfo}>
                  <h4>{item.title}</h4>
                  <p>{item.desc}</p>
                  <div className={styles.articleDate}>{item.date}</div>
                </div>
              </div>
            ))}
          </div>

          {/* 右侧专题栏 */}
          <div className={styles.sidebarRight}>
            <img 
              src="https://picsum.photos/280/100?random=7" 
              alt="香山国际关节成形外科峰会" 
              className={styles.sidebarBanner}
            />
            <h3>
              专题 
              <a href="#" className={styles.more}>更多</a>
            </h3>
            {topicItems.map(item => (
              <div key={item.id} className={styles.topicItem}>
                <img src={item.imgSrc} alt={item.text} />
                <p>{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        // 详情页
        <div className={styles.articleDetail}>
          <button className={styles.backBtn} onClick={backToList}>← 返回列表</button>
          {selectedArticleId && articles[selectedArticleId] && (
            <>
              <h2 className={styles.detailTitle}>{articles[selectedArticleId].title}</h2>
              <div className={styles.meta}>发布时间：{articles[selectedArticleId].date}</div>
              <div 
                className={styles.detailContent}
                dangerouslySetInnerHTML={{ __html: articles[selectedArticleId].content }}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
};

// 默认导出组件
export default MessagePage;