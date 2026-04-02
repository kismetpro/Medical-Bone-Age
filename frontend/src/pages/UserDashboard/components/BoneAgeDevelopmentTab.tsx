import React, { useState, useMemo } from 'react';
import { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Scatter, Line, Legend } from 'recharts';
import { RefreshCw, Download, Info } from 'lucide-react';
import styles from '../UserDashboard.module.css';
import {
    generateBoneAgeData,
    calculateStatistics,
    generateNormalRangeData,
    exportBoneAgeDataToCSV,
    type GeneratedData,
} from '../../../lib/boneAgeDevelopment';

const BoneAgeDevelopmentTab: React.FC = () => {
    const [gender, setGender] = useState<'male' | 'female' | 'both'>('both');
    const [showNormalRange, setShowNormalRange] = useState(true);
    const [dataPoints, setDataPoints] = useState<number>(50);
    const [generatedData, setGeneratedData] = useState<GeneratedData | null>(null);

    const generateData = () => {
        const data = generateBoneAgeData(dataPoints, dataPoints);
        setGeneratedData(data);
    };

    const normalRangeData = useMemo(() => generateNormalRangeData(20, 0.5, 1.0), []);

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

    const statistics = useMemo(() => {
        if (!generatedData) return null;
        return calculateStatistics(generatedData);
    }, [generatedData]);

    const handleExport = () => {
        if (generatedData) {
            exportBoneAgeDataToCSV(generatedData);
        }
    };

    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.resultsCard} style={{ width: '100%', gridColumn: '1 / -1' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0 }}>骨龄发展规律数据生成器</h3>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            className={styles.btnPrimary}
                            onClick={generateData}
                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                            <RefreshCw size={16} /> 生成数据
                        </button>
                        {generatedData && (
                            <button
                                onClick={handleExport}
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