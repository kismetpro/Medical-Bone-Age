import type { AuthRole } from '../../context/AuthContext';

export interface PredictionRecord { 
    id: string; 
    user_id: number; 
    username?: string; 
    timestamp: number; 
    filename: string; 
    predicted_age_years: number; 
    gender: string; 
}

export interface PredictionDetail extends PredictionRecord { 
    real_age_years?: number; 
    predicted_adult_height?: number; 
    anomalies?: Array<{ type: string; score: number; coord: number[] }>; 
    heatmap_base64?: string; 
    rus_chn_details?: { total_score?: number }; 
}

export interface PatientUser { 
    id: number; 
    username: string; 
    created_at: string; 
}

export interface QaItem { 
    qid: number; 
    owner: string; 
    text: string; 
    image: string; 
    reply: string; 
    createTime: string; 
}

export interface ManagedAccount { 
    id: number; 
    username: string; 
    role: AuthRole; 
    created_at: string; 
}

export type ActiveTab = 'records' | 'accounts' | 'consultation' | 'community';

export type ChatMessage = { 
    role: 'user' | 'assistant'; 
    text: string 
};

export const roleLabelMap: Record<AuthRole, string> = { 
    user: '个人用户', 
    doctor: '临床医生', 
    super_admin: '超级管理员' 
};
