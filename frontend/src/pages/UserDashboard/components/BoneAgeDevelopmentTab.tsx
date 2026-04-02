import React, { useState, useMemo } from 'react';
import { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Scatter, Line, Legend } from 'recharts';
import { RefreshCw, Download, Info } from 'lucide-react';
import styles from '../UserDashboard.module.css';

interface BoneAgeDataPoint {
    age: number; // 实际年龄（岁）
    boneAge: number; // 骨龄（岁）
    gender: 'male' | 'female';
    status: 'normal' | 'advanced' | 'delayed';
}

interface GeneratedData {
    male: BoneAgeDataPoint[];
    female: BoneAgeDataPoint[];
}

const BoneAgeDevelopmentTab: React.FC = () => {
    const [gender, setGender] = useState<'male' | 'female' | 'both'>('both');
    const [showNormalRange, setShowNormalRange] = useState(true);
    const [dataPoints, setDataPoints] = useState<number>(50);
    const [generatedData, setGeneratedData] = useState<GeneratedData | null>(null);

    // 骨龄发展规律参数
    const developmentParams = {
        male: {
            // 男孩骨龄发展速度（岁/年）- 不同年龄段
            velocity: [
                { minAge: 0, maxAge: 2, rate: 1.2 }, // 婴幼儿期发展较快
                { minAge: 2, maxAge: 6, rate: 1.0 }, // 幼儿期正常发展
                { minAge: 6, maxAge: 10, rate: 0.9 }, // 学龄期稍慢
                { minAge: 10, maxAge: 14, rate: 1.1 }, // 青春期加速
                { minAge: 14, maxAge: 18, rate: 0.8 }, // 青春期后期减缓
                { minAge: 18, maxAge: 25, rate: 0.3 }, // 成年期趋缓
            ],
            // 骨龄与实际年龄的正常差异范围（岁）
            normalRange: 1.0,
            // 青春期加速年龄范围
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

    // 生成符合骨龄发展规律的数据
    const generateBoneAgeData = () => {
        const maleData: BoneAgeDataPoint[] = [];
        const femaleData: BoneAgeDataPoint[] = [];

        // 生成男性数据
        for (let i = 0; i < dataPoints; i++) {
            const age = Math.random() * 20; // 0-20岁随机
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

        // 生成女性数据
        for (let i = 0; i < dataPoints; i++) {
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

        // 按年龄排序
        maleData.sort((a, b) => a.age - b.age);
        femaleData.sort((a, b) => a.age - b.age);

        setGeneratedData({ male: maleData, female: femaleData });
    };

    // 根据年龄和性别计算骨龄
    const calculateBoneAge = (age: number, gender: 'male' | 'female'): number => {
        const params = developmentParams[gender];

        // 基础骨龄计算
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

        // 添加青春期加速效应
        const { start, peak, end } = params.pubertalAcceleration;
        if (age >= start && age <= end) {
            // 使用抛物线模拟青春期加速
            const acceleration = 1 - Math.pow((age - peak) / ((end - start) / 2), 2);
            boneAge += acceleration * 0.5; // 青春期额外增加
        }

        // 添加随机变异（±0.8岁范围内的正态分布变异）
        const randomVariation = (Math.random() - 0.5) * 1.6;
        boneAge += randomVariation;

        // 确保骨龄不小于0
        return Math.max(0, boneAge);
    };

    // 生成正常范围数据
    const normalRangeData = useMemo(() => {
        const data = [];
        for (let age = 0; age <= 20; age += 0.5) {
            data.push({
                age,
                upper: age + 1,
                lower: age - 1,
            });
        }
        return data;
    }, []);

    // 获取显示数据
    const displayData = useMemo(() => {
        if (!generatedData) return [];

        const data: any[] = [];
        if (gender === 'male' || gender === 'both') {
            generatedData.male.forEach(d => {
                data.push({
                    ...d,
                    name: 'male',
                    fill: d.status === 'normal' ? '#3b82f6' : d.status === 'advanced' ? '#ef4444' : '#22c55e',
                });
            });
        }
        if (gender === 'female' || gender === 'both') {
            generatedData.female.forEach(d => {
                data.push({
                    ...d,
                    name: 'female',
                    fill: d.status === 'normal' ? '#ec4899' : d.status === 'advanced' ? '#ef4444' : '#22c55e',
                });
            });
        }
        return data;
    }, [generatedData, gender]);

    // 统计信息
    const statistics = useMemo(() => {
        if (!generatedData) return null;

        const allData = [...generatedData.male, ...generatedData.female];
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
    }, [generatedData]);

    // 导出数据
    const exportData = () => {
        if (!generatedData) return;

        const allData = [
            ...generatedData.male,
            ...generatedData.female,
        ];

        const csvContent = [
            '实际年龄(岁),骨龄(岁),性别,状态',
            ...allData.map(d => `${d.age},${d.boneAge},${d.gender},${d.status}`),
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `骨龄发展规律数据_${new Date().toLocaleDateString()}.csv`;
        link.click();
    };

    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.resultsCard} style={{ width: '100%', gridColumn: '1 / -1' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0 }}>骨龄发展规律数据生成器</h3>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            className={styles.btnPrimary}
                            onClick={generateBoneAgeData}
                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                            <RefreshCw size={16} /> 生成数据
                        </button>
                        {generatedData && (
                            <button
                                onClick={exportData}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '6px',
                                    border: '1px solid #e2e8f0',
                                    background: 'white',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                }}
                            >
                                <Download size={16} /> 导出CSV
                            </button>
                        )}
                    </div>
                </div>

                {/* 控制面板 */}
                <div style={{
                    border: '1px solid #e2e8f0',
                    borderRadius: 12,
                    padding: '1rem',
                    marginBottom: '1rem',
                    background: '#f8fafc',
                }}>
                    <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>性别筛选</label>
                            <select
                                value={gender}
                                onChange={(e) => setGender(e.target.value as any)}
                                style={{
                                    width: '100%',
                                    padding: '0.5rem',
                                    borderRadius: '6px',
                                    border: '1px solid #e2e8f0',
                                }}
                            >
                                <option value="both">全部</option>
                                <option value="male">男性</option>
                                <option value="female">女性</option>
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>数据点数量</label>
                            <input
                                type="range"
                                min="10"
                                max="200"
                                value={dataPoints}
                                onChange={(e) => setDataPoints(Number(e.target.value))}
                                style={{ width: '100%' }}
                            />
                            <div style={{ textAlign: 'center', fontSize: '0.9rem', color: '#64748b' }}>{dataPoints} 个点</div>
                        </div>
                        <div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={showNormalRange}
                                    onChange={(e) => setShowNormalRange(e.target.checked)}
                                />
                                <span style={{ fontWeight: 500 }}>显示正常范围</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* 数据可视化 */}
                <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: '1rem', background: '#fff' }}>
                    <div style={{ height: 400, marginBottom: '1rem' }}>
                        <ResponsiveContainer>
                            <ComposedChart margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis
                                    type="number"
                                    dataKey="age"
                                    name="实际年龄"
                                    unit="岁"
                                    domain={[0, 20]}
                                    label={{ value: '实际年龄 (岁)', position: 'bottom', offset: 0 }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="boneAge"
                                    name="骨龄"
                                    unit="岁"
                                    domain={[0, 20]}
                                    label={{ value: '骨龄 (岁)', angle: -90, position: 'insideLeft' }}
                                />
                                <Tooltip
                                    formatter={(value: any, name: any) => {
                                        if (name === 'boneAge') return [`${value} 岁`, '骨龄'];
                                        if (name === 'upper') return [`${value} 岁`, '正常上限'];
                                        if (name === 'lower') return [`${value} 岁`, '正常下限'];
                                        return [value, name];
                                    }}
                                    labelFormatter={(value) => `实际年龄: ${value} 岁`}
                                />
                                <Legend />

                                {/* 正常范围区域 */}
                                {showNormalRange && (
                                    <>
                                        <Line
                                            data={normalRangeData}
                                            type="monotone"
                                            dataKey="upper"
                                            stroke="#94a3b8"
                                            strokeDasharray="5 5"
                                            dot={false}
                                            name="正常上限 (+1岁)"
                                        />
                                        <Line
                                            data={normalRangeData}
                                            type="monotone"
                                            dataKey="lower"
                                            stroke="#94a3b8"
                                            strokeDasharray="5 5"
                                            dot={false}
                                            name="正常下限 (-1岁)"
                                        />
                                    </>
                                )}

                                {/* 理想线 */}
                                <Line
                                    data={normalRangeData}
                                    type="monotone"
                                    dataKey="age"
                                    stroke="#e2e8f0"
                                    dot={false}
                                    name="理想线 (骨龄=实际年龄)"
                                />

                                {/* 数据点 */}
                                <Scatter
                                    data={displayData}
                                    dataKey="boneAge"
                                    fill="#8884d8"
                                    name="骨龄数据点"
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>

                    {/* 图例说明 */}
                    <div style={{
                        display: 'flex',
                        gap: '2rem',
                        justifyContent: 'center',
                        marginBottom: '1rem',
                        padding: '1rem',
                        background: '#f8fafc',
                        borderRadius: 8,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#3b82f6' }}></div>
                            <span>男性 - 正常</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ec4899' }}></div>
                            <span>女性 - 正常</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444' }}></div>
                            <span>早熟 (骨龄 &gt; 实际年龄1岁)</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#22c55e' }}></div>
                            <span>晚熟 (骨龄 &lt; 实际年龄1岁)</span>
                        </div>
                    </div>
                </div>

                {/* 统计信息 */}
                {statistics && (
                    <div style={{
                        border: '1px solid #e2e8f0',
                        borderRadius: 12,
                        padding: '1rem',
                        marginTop: '1rem',
                        background: '#fff',
                    }}>
                        <h4 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Info size={18} /> 数据统计
                        </h4>
                        <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
                            <div style={{ textAlign: 'center', padding: '1rem', background: '#f8fafc', borderRadius: 8 }}>
                                <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0f172a' }}>{statistics.total}</div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b' }}>总数据点</div>
                            </div>
                            <div style={{ textAlign: 'center', padding: '1rem', background: '#f0fdf4', borderRadius: 8 }}>
                                <div style={{ fontSize: '2rem', fontWeight: 700, color: '#22c55e' }}>{statistics.normal}</div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b' }}>正常 ({statistics.normalPercent}%)</div>
                            </div>
                            <div style={{ textAlign: 'center', padding: '1rem', background: '#fef2f2', borderRadius: 8 }}>
                                <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ef4444' }}>{statistics.advanced}</div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b' }}>早熟 ({statistics.advancedPercent}%)</div>
                            </div>
                            <div style={{ textAlign: 'center', padding: '1rem', background: '#eff6ff', borderRadius: 8 }}>
                                <div style={{ fontSize: '2rem', fontWeight: 700, color: '#3b82f6' }}>{statistics.delayed}</div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b' }}>晚熟 ({statistics.delayedPercent}%)</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* 骨龄发展规律说明 */}
                <div style={{
                    border: '1px solid #e2e8f0',
                    borderRadius: 12,
                    padding: '1.5rem',
                    marginTop: '1rem',
                    background: '#fff',
                }}>
                    <h4 style={{ margin: '0 0 1rem 0' }}>骨龄发展规律说明</h4>
                    <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                        <div>
                            <h5 style={{ margin: '0 0 0.5rem 0', color: '#3b82f6' }}>男孩发育特点</h5>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.9rem', color: '#475569' }}>
                                <li>青春期加速期：11-16岁，峰值约13岁</li>
                                <li>骨龄通常略大于实际年龄</li>
                                <li>青春期前发展相对平稳</li>
                                <li>青春期后发展迅速减缓</li>
                            </ul>
                        </div>
                        <div>
                            <h5 style={{ margin: '0 0 0.5rem 0', color: '#ec4899' }}>女孩发育特点</h5>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.9rem', color: '#475569' }}>
                                <li>青春期加速期：9-13岁，峰值约11岁</li>
                                <li>比男孩早发育约2年</li>
                                <li>青春期发展速度更快</li>
                                <li>更早进入发育平台期</li>
                            </ul>
                        </div>
                        <div>
                            <h5 style={{ margin: '0 0 0.5rem 0', color: '#22c55e' }}>正常范围标准</h5>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.9rem', color: '#475569' }}>
                                <li>骨龄与实际年龄差异在±1岁内为正常</li>
                                <li>差异 &gt; 1岁为早熟倾向</li>
                                <li>差异&lt;-1岁为晚熟倾向</li>
                                <li>个体差异是正常现象</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BoneAgeDevelopmentTab;