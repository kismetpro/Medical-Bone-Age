// 文件路径: src/pages/UserDashboard/tabsConfig.ts
import PredictTab from './components/PredictTab';
import ImagePreprocessingTab from './components/ImagePreprocessingTab';
import HistoryTab from './components/HistoryTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';
import SettingsTab from './components/SettingsTab';

export const TABS_CONFIG = {
  predict: {
    id: 'predict',
    label: '骨龄预测',
    component: PredictTab,
  },
  preprocessing: {
    id: 'preprocessing',
    label: '图像预处理',
    component: ImagePreprocessingTab,
  },
  history: {
    id: 'history',
    label: '评估历史',
    component: HistoryTab,
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
  settings: {
    id: 'settings',
    label: '系统设置',
    component: SettingsTab,
  },
};

export type TabId = keyof typeof TABS_CONFIG;
