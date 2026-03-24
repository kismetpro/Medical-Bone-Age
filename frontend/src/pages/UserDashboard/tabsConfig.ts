import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bot,
  Bone,
  Calculator,
  Edit3,
  History as HistoryIcon,
  Image as ImageIcon,
  MessageSquare,
  Settings,
} from 'lucide-react';

export type UserDashboardTab =
  | 'predict'
  | 'history'
  | 'joint-grade'
  | 'formula'
  | 'manual-grade'
  | 'consultation'
  | 'community'
  | 'preprocessing'
  | 'settings';

export type UserDashboardTabGroup = 'analysis' | 'care' | 'system';

export interface UserDashboardTabConfig {
  id: UserDashboardTab;
  label: string;
  icon: LucideIcon;
  group: UserDashboardTabGroup;
}

export const USER_DASHBOARD_DEFAULT_TAB: UserDashboardTab = 'predict';

export const USER_DASHBOARD_TABS: UserDashboardTabConfig[] = [
  { id: 'predict', label: '预测评估', icon: Activity, group: 'analysis' },
  { id: 'history', label: '预测记录', icon: HistoryIcon, group: 'analysis' },
  { id: 'joint-grade', label: '小关节分级', icon: Bone, group: 'analysis' },
  { id: 'formula', label: '公式法预测骨龄', icon: Calculator, group: 'analysis' },
  { id: 'manual-grade', label: '手动分级计算', icon: Edit3, group: 'analysis' },
  { id: 'consultation', label: '智能问诊', icon: Bot, group: 'care' },
  { id: 'community', label: '问答社区', icon: MessageSquare, group: 'care' },
  { id: 'preprocessing', label: '图像预处理', icon: ImageIcon, group: 'system' },
  { id: 'settings', label: '系统设置', icon: Settings, group: 'system' },
];
