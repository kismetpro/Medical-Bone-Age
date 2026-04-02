export interface BoneAgeDataPoint {
    age: number;
    boneAge: number;
    gender: 'male' | 'female';
    status: 'normal' | 'advanced' | 'delayed';
}

export interface GeneratedData {
    male: BoneAgeDataPoint[];
    female: BoneAgeDataPoint[];
}

export interface VelocityStage {
    minAge: number;
    maxAge: number;
    rate: number;
}

export interface PubertalAcceleration {
    start: number;
    peak: number;
    end: number;
}

export interface DevelopmentParams {
    velocity: VelocityStage[];
    normalRange: number;
    pubertalAcceleration: PubertalAcceleration;
}

export const DEVELOPMENT_PARAMS: Record<'male' | 'female', DevelopmentParams> = {
    male: {
        velocity: [
            { minAge: 0, maxAge: 2, rate: 1.2 },
            { minAge: 2, maxAge: 6, rate: 1.0 },
            { minAge: 6, maxAge: 10, rate: 0.9 },
            { minAge: 10, maxAge: 14, rate: 1.1 },
            { minAge: 14, maxAge: 18, rate: 0.8 },
            { minAge: 18, maxAge: 25, rate: 0.3 },
        ],
        normalRange: 1.0,
        pubertalAcceleration: { start: 11, peak: 13, end: 16 },
    },
    female: {
        velocity: [
            { minAge: 0, maxAge: 2, rate: 1.3 },
            { minAge: 2, maxAge: 6, rate: 1.05 },
            { minAge: 6, maxAge: 9, rate: 0.95 },
            { minAge: 9, maxAge: 12, rate: 1.15 },
            { minAge: 12, maxAge: 15, rate: 0.85 },
            { minAge: 15, maxAge: 20, rate: 0.4 },
        ],
        normalRange: 1.0,
        pubertalAcceleration: { start: 9, peak: 11, end: 13 },
    },
};

export function calculateBoneAge(age: number, gender: 'male' | 'female'): number {
    const params = DEVELOPMENT_PARAMS[gender];

    let boneAge = 0;
    let lastAge = 0;

    for (const stage of params.velocity) {
        if (age <= stage.minAge) break;

        const stageAge = Math.min(age, stage.maxAge) - Math.max(lastAge, stage.minAge);
        if (stageAge > 0) {
            boneAge += stageAge * stage.rate;
        }
        lastAge = stage.maxAge;
        if (age <= stage.maxAge) break;
    }

    const { start, peak, end } = params.pubertalAcceleration;
    if (age >= start && age <= end) {
        const acceleration = 1 - Math.pow((age - peak) / ((end - start) / 2), 2);
        boneAge += acceleration * 0.5;
    }

    const randomVariation = (Math.random() - 0.5) * 1.6;
    boneAge += randomVariation;

    return Math.max(0, boneAge);
}

export function generateBoneAgeData(
    maleCount: number,
    femaleCount: number
): GeneratedData {
    const maleData: BoneAgeDataPoint[] = [];
    const femaleData: BoneAgeDataPoint[] = [];

    for (let i = 0; i < maleCount; i++) {
        const age = Math.random() * 20;
        const boneAge = calculateBoneAge(age, 'male');
        const diff = boneAge - age;
        let status: 'normal' | 'advanced' | 'delayed' = 'normal';
        if (diff > 1) status = 'advanced';
        else if (diff < -1) status = 'delayed';

        maleData.push({
            age: parseFloat(age.toFixed(2)),
            boneAge: parseFloat(boneAge.toFixed(2)),
            gender: 'male',
            status,
        });
    }

    for (let i = 0; i < femaleCount; i++) {
        const age = Math.random() * 20;
        const boneAge = calculateBoneAge(age, 'female');
        const diff = boneAge - age;
        let status: 'normal' | 'advanced' | 'delayed' = 'normal';
        if (diff > 1) status = 'advanced';
        else if (diff < -1) status = 'delayed';

        femaleData.push({
            age: parseFloat(age.toFixed(2)),
            boneAge: parseFloat(boneAge.toFixed(2)),
            gender: 'female',
            status,
        });
    }

    maleData.sort((a, b) => a.age - b.age);
    femaleData.sort((a, b) => a.age - b.age);

    return { male: maleData, female: femaleData };
}

export interface Statistics {
    total: number;
    normal: number;
    advanced: number;
    delayed: number;
    normalPercent: string;
    advancedPercent: string;
    delayedPercent: string;
}

export function calculateStatistics(data: GeneratedData): Statistics | null {
    const allData = [...data.male, ...data.female];
    const normalCount = allData.filter(d => d.status === 'normal').length;
    const advancedCount = allData.filter(d => d.status === 'advanced').length;
    const delayedCount = allData.filter(d => d.status === 'delayed').length;

    return {
        total: allData.length,
        normal: normalCount,
        advanced: advancedCount,
        delayed: delayedCount,
        normalPercent: ((normalCount / allData.length) * 100).toFixed(1),
        advancedPercent: ((advancedCount / allData.length) * 100).toFixed(1),
        delayedPercent: ((delayedCount / allData.length) * 100).toFixed(1),
    };
}

export interface NormalRangePoint {
    age: number;
    upper: number;
    lower: number;
}

export function generateNormalRangeData(
    maxAge: number = 20,
    step: number = 0.5,
    range: number = 1.0
): NormalRangePoint[] {
    const data: NormalRangePoint[] = [];
    for (let age = 0; age <= maxAge; age += step) {
        data.push({
            age,
            upper: age + range,
            lower: age - range,
        });
    }
    return data;
}

export function exportBoneAgeDataToCSV(data: GeneratedData): void {
    const allData = [...data.male, ...data.female];
    const csvContent = [
        '实际年龄(岁),骨龄(岁),性别,状态',
        ...allData.map(d => `${d.age},${d.boneAge},${d.gender},${d.status}`),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `骨龄发展规律数据_${new Date().toLocaleDateString()}.csv`;
    link.click();
}
