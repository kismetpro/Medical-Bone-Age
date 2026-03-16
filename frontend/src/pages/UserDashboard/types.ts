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
    joint_detect_13?: {
        hand_side: string;
        detected_count: number;
        plot_image_base64?: string | null;
    };
    anomalies?: Array<{
        type: string;
        score: number;
        coord: number[];
    }>;
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
    brightness: 100,
    contrast: 13.24,
    invert: false,
    scale: 1,
    usePreprocessing: false
};
