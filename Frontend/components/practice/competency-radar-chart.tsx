'use client'

/**
 * Competency Radar Chart
 * 
 * SVG-based radar/spider chart showing balance between different competencies:
 * - Semantic Accuracy (BERTScore)
 * - LLM Quality Score
 * - Content Structure (STAR overall)
 * - Relevance
 * - Coherence
 */

import React, { useMemo } from 'react'
import { Radar } from 'lucide-react'

interface CompetencyRadarChartProps {
    data: {
        semanticAccuracy: number  // 0-100 (BERTScore F1 * 100)
        qualityScore: number      // 0-100 (LLM Judge * 10)
        structureScore: number    // 0-100 (STAR overall)
        relevance: number         // 0-100 (content_relevance * 20)
        coherence: number         // 0-100 (coherence_score * 20)
    }
    size?: number
    className?: string
}

const competencyLabels = [
    { key: 'semanticAccuracy', label: 'Semantic Match', color: '#818cf8' },
    { key: 'qualityScore', label: 'Quality', color: '#34d399' },
    { key: 'structureScore', label: 'Structure', color: '#fbbf24' },
    { key: 'relevance', label: 'Relevance', color: '#f472b6' },
    { key: 'coherence', label: 'Coherence', color: '#60a5fa' },
]

export function CompetencyRadarChart({
    data,
    size = 280,
    className = ''
}: CompetencyRadarChartProps) {
    const center = size / 2
    const radius = (size - 80) / 2  // Leave room for labels
    const levels = 5  // Number of concentric circles

    // Calculate points for the radar polygon
    const points = useMemo(() => {
        const numAxes = competencyLabels.length
        const angleStep = (Math.PI * 2) / numAxes

        return competencyLabels.map((comp, i) => {
            const angle = angleStep * i - Math.PI / 2  // Start from top
            const value = data[comp.key as keyof typeof data] || 0
            const normalizedValue = Math.min(100, Math.max(0, value)) / 100

            return {
                x: center + Math.cos(angle) * radius * normalizedValue,
                y: center + Math.sin(angle) * radius * normalizedValue,
                labelX: center + Math.cos(angle) * (radius + 30),
                labelY: center + Math.sin(angle) * (radius + 30),
                axisX: center + Math.cos(angle) * radius,
                axisY: center + Math.sin(angle) * radius,
                value,
                label: comp.label,
                color: comp.color
            }
        })
    }, [data, center, radius])

    // Create polygon path
    const polygonPath = points.map((p, i) =>
        `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`
    ).join(' ') + ' Z'

    // Generate concentric circles
    const circles = Array.from({ length: levels }, (_, i) => {
        const levelRadius = (radius / levels) * (i + 1)
        return (
            <circle
                key={i}
                cx={center}
                cy={center}
                r={levelRadius}
                fill="none"
                stroke="rgba(100, 116, 139, 0.3)"
                strokeWidth="1"
            />
        )
    })

    // Generate axis lines
    const axisLines = points.map((p, i) => (
        <line
            key={i}
            x1={center}
            y1={center}
            x2={p.axisX}
            y2={p.axisY}
            stroke="rgba(100, 116, 139, 0.4)"
            strokeWidth="1"
        />
    ))

    // Calculate average score
    const avgScore = useMemo(() => {
        const values = Object.values(data)
        return Math.round(values.reduce((a, b) => a + b, 0) / values.length)
    }, [data])

    return (
        <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-5 border border-slate-700/50 ${className}`}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Radar className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-lg font-semibold text-white">Competency Balance</h3>
                </div>
                <div className="text-right">
                    <span className="text-2xl font-bold text-indigo-400">{avgScore}</span>
                    <span className="text-sm text-slate-400">/100</span>
                </div>
            </div>

            <div className="flex justify-center">
                <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                    {/* Background circles */}
                    {circles}

                    {/* Axis lines */}
                    {axisLines}

                    {/* Data polygon */}
                    <path
                        d={polygonPath}
                        fill="rgba(129, 140, 248, 0.25)"
                        stroke="rgb(129, 140, 248)"
                        strokeWidth="2"
                    />

                    {/* Data points */}
                    {points.map((p, i) => (
                        <circle
                            key={i}
                            cx={p.x}
                            cy={p.y}
                            r="5"
                            fill={p.color}
                            stroke="white"
                            strokeWidth="2"
                        />
                    ))}

                    {/* Labels */}
                    {points.map((p, i) => (
                        <text
                            key={i}
                            x={p.labelX}
                            y={p.labelY}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            className="fill-slate-300 text-xs font-medium"
                        >
                            {p.label}
                        </text>
                    ))}

                    {/* Center label */}
                    <text
                        x={center}
                        y={center}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        className="fill-slate-500 text-xs"
                    >
                        Avg: {avgScore}%
                    </text>
                </svg>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-3 mt-4">
                {points.map((p, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                        <div
                            className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: p.color }}
                        />
                        <span className="text-xs text-slate-400">{p.label}: {Math.round(p.value)}%</span>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default CompetencyRadarChart
