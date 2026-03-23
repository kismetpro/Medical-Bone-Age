// 文件路径: src/pages/UserDashboard/tabsConfig.ts
import PredictTab from './components/PredictTab';
import HistoryTab from './components/HistoryTab';
import JointGradeTab from './components/JointGradeTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';

export const TABS_CONFIG = {
  predict: {
    id: 'predict',
    label: '骨龄预测',
    component: PredictTab,
  },
  history: {
    id: 'history',
    label: '评估历史',
    component: HistoryTab,
  },
  'joint-grade': {
    id: 'joint-grade',
    label: '小关节分级',
    component: JointGradeTab,
  },
  consultation: {
    id: 'consultation',
    label: '专家咨询',
    component: ConsultationPage,
  },
  community: {
    id: 'community',
    label: '交流社区',
    component: CommunityPage,
  },
};

export type TabId = keyof typeof TABS_CONFIG;