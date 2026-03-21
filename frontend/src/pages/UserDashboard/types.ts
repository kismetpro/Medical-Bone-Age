import type { AnomalyItem, ForeignObjectDetection } from '../../lib/prediction';

export interface RusChnDetail {
    name: string;
    stage: number;
    score: number;
}

export interface RusChnReport {
    total_score: number;
    details: RusChnDetail[];
    target_score_lookup: number;
}

export interface JointGrade {
    model_joint?: string;
    grade_idx?: number;
    grade_raw?: number;
    score?: number;
    status?: 'ok' | 'model_missing' | 'crop_invalid' | 'semantic_imputed' | 'semantic_default';
    imputed?: boolean;
    source_joint?: string;
}

export interface PredictionResult {
    id: string;
    timestamp: number;
    filename: string;
    predicted_age_months: number;
    predicted_age_years: number;
    gender: string;
    real_age_years?: number;
    rus_chn_details?: RusChnReport;
    heatmap_base64?: string;
    detection_image_base64?: string;
    predicted_adult_height?: number;
    foreign_object_detection?: ForeignObjectDetection;
    joint_detect_13?: {
        hand_side: string;
        detected_count: number;
        plot_image_base64?: string | null;
    };
    joint_grades?: Record<string, JointGrade>;
    joint_semantic_13?: Record<string, JointGrade>;
    joint_rus_total_score?: number;
    joint_rus_details?: RusChnDetail[];
    anomalies?: AnomalyItem[];
}

export interface BoneAgePoint {
    id: number;
    user_id: number;
    point_time: number;
    bone_age_years: number;
    chronological_age_years?: number | null;
    source: string;
    prediction_id?: string | null;
    note?: string;
}

export interface BoneAgeTrend {
    points: number;
    enough: boolean;
    latex: string;
    r2?: number;
    coefficients?: {
        intercept: number;
        time: number;
        chronological_age: number;
    };
}

export interface ImageSettings {
    brightness: number;
    contrast: number;
    invert: boolean;
    scale: number;
    usePreprocessing: boolean;
}



export const DEFAULT_SETTINGS: ImageSettings = {
brightness: 100, // 亮度初始值为 100%
    contrast: 1,     // 对比度初始值为 1 (注意这里是 1，不是 100)
    invert: false,   // 不反相
    usePreprocessing: false
};