'use client'

import * as React from 'react'
import { useParams } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  ArrowLeft,
  FileX,
  Eye,
  Mic,
  Brain,
  Award,
  CheckCircle,
  TrendingUp,
  MessageSquare,
  Volume2,
  Sparkles,
  BarChart3,
  Lightbulb,
  Target,
  PlayCircle,
  ChevronRight,
  Star,
  StarHalf
} from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { EmotionTimeline } from '@/components/reports/emotion-timeline'
import { CompetencyRadarChart } from '@/components/practice/competency-radar-chart'
import { LLMJudgeFeedback } from '@/components/practice/llm-judge-feedback'
import { STARBreakdown } from '@/components/practice/star-breakdown'

type TabType = 'overview' | 'facial' | 'voice' | 'content' | 'detailed'

// Advanced Score Normalization: Linear Rescaling with Baselines
// Formula: Rescaled = max(0, (Raw - b) / (1 - b))
const rescaleScore = (raw: number, baseline: number = 0.70) => {
  const score = raw > 1 ? raw / 100 : raw
  const rescaled = Math.max(0, (score - baseline) / (1 - baseline))
  return Math.round(rescaled * 100)
}

const getScoreColor = (rescaledScore: number) => {
  if (rescaledScore >= 90) return 'text-green-400'
  if (rescaledScore >= 70) return 'text-blue-400'
  if (rescaledScore >= 40) return 'text-amber-400'
  return 'text-orange-400'
}

const getScoreBg = (rescaledScore: number) => {
  if (rescaledScore >= 90) return 'bg-green-500'
  if (rescaledScore >= 70) return 'bg-blue-500'
  if (rescaledScore >= 40) return 'bg-amber-500'
  return 'bg-orange-500'
}

const getScoreLabel = (rescaledScore: number) => {
  if (rescaledScore >= 90) return 'Excellent'
  if (rescaledScore >= 70) return 'Good'
  if (rescaledScore >= 40) return 'Average'
  return 'Needs Restructuring'
}

const getStarRating = (rescaledScore: number) => {
  if (rescaledScore >= 90) return 5
  if (rescaledScore >= 70) return 4
  if (rescaledScore >= 40) return 3
  if (rescaledScore >= 20) return 2
  return 1
}

export default function ReportDetailPage() {
  const params = useParams()
  const [report, setReport] = React.useState<any>(null)
  const [notFound, setNotFound] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<TabType>('overview')

  React.useEffect(() => {
    // Load report from localStorage
    const storedReports = JSON.parse(localStorage.getItem('qace_reports') || '[]')
    const foundReport = storedReports.find((r: any) => r.id === params.reportId)

    if (foundReport) {
      setReport(foundReport)
    } else {
      setNotFound(true)
    }
  }, [params.reportId])

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <Award className="h-4 w-4" /> },
    { id: 'facial', label: 'Facial', icon: <Eye className="h-4 w-4" /> },
    { id: 'voice', label: 'Vocal', icon: <Volume2 className="h-4 w-4" /> },
    { id: 'content', label: 'Content', icon: <Brain className="h-4 w-4" /> },
    { id: 'detailed', label: 'Deep Analysis', icon: <Sparkles className="h-4 w-4" /> },
  ]

  if (notFound) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <FileX className="h-12 w-12 text-foreground/40 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Report Not Found</h3>
          <p className="text-foreground/60 mb-4">
            This report doesn&apos;t exist or may have been deleted.
          </p>
          <Button asChild variant="primary">
            <Link href="/reports">Back to Reports</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <div className="animate-pulse">
            <div className="h-8 w-48 bg-foreground/10 rounded mx-auto mb-4"></div>
            <div className="h-4 w-32 bg-foreground/10 rounded mx-auto"></div>
          </div>
        </div>
      </div>
    )
  }

  // Pre-calculate rescaled mastery score
  const rawMastery = report.analysis?.coaching?.progress_position || 50
  const rescaledMastery = rescaleScore(rawMastery)

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/reports">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Reports
          </Link>
        </Button>
      </div>

      {/* Title Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text mb-2">Practice Session Report</h1>
          <p className="text-foreground/60">
            Analysis completed on {report.createdAt ? new Date(report.createdAt).toLocaleDateString() : 'Unknown Date'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant={
              rescaledMastery >= 90
                ? 'success'
                : rescaledMastery >= 70
                  ? 'info'
                  : 'error'
            }
            className="text-lg px-4 py-2"
          >
            {getScoreLabel(rescaledMastery)}
          </Badge>
        </div>
      </div>

      {/* AI Synthesis Header */}
      {report.analysis?.coaching?.generated_feedback && (
        <Card className="bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-blue-500/20 border-indigo-500/20 overflow-hidden">
          <div className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-indigo-500/20 rounded-xl text-indigo-400">
                <Sparkles className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-bold uppercase tracking-wider text-indigo-300">AI Synthesis</h4>
                <p className="text-lg text-white font-medium leading-relaxed italic">
                  "{report.analysis.coaching.generated_feedback}"
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Main Content Card */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-md overflow-hidden p-0">
        <div className="p-6 space-y-8">
          {/* Tab Navigation */}
          <div className="flex gap-2 p-1 bg-background/50 rounded-lg">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-accent text-accent-foreground shadow-sm'
                    : 'text-foreground/60 hover:text-foreground hover:bg-background/50'
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="min-h-[300px] space-y-8">
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-8 animate-in fade-in duration-500">
                {/* Answer Quality Verdict & Progress Bar */}
                <div className="p-6 rounded-2xl bg-slate-800/40 border border-slate-700/50 space-y-6">
                  <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center p-2 bg-accent/10 rounded-lg text-accent mb-2">
                      <Target className="h-5 w-5" />
                    </div>
                    <div className="flex flex-col items-center">
                      <h4 className={cn("text-2xl font-black mb-1", getScoreColor(rescaledMastery))}>
                        {report.analysis?.coaching?.quality_interpretation || getScoreLabel(rescaledMastery)}
                      </h4>
                      <StarRating rating={getStarRating(rescaledMastery)} />
                    </div>
                    <p className="text-slate-300 max-w-lg mx-auto leading-relaxed text-sm mt-3">
                      {report.analysis?.coaching?.quality_description || 'Your response shows understanding but could use more detail to increase impact.'}
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Mastery Level</span>
                      <span className={cn("text-lg font-black", getScoreColor(rescaledMastery))}>
                        {rescaledMastery}%
                      </span>
                    </div>
                    {/* Adjusted to 4 segments (25% each) based on user screenshot */}
                    <div className="flex gap-1.5 h-3">
                      {[1, 2, 3, 4].map((segment) => {
                        const threshold = segment * 25
                        const isActive = rescaledMastery >= threshold - 12.5
                        const isFullyActive = rescaledMastery >= threshold
                        return (
                          <div key={segment} className={cn("flex-1 rounded-sm transition-all duration-700", isFullyActive ? getScoreBg(rescaledMastery) : isActive ? `${getScoreBg(rescaledMastery)}/40` : "bg-slate-700/30")} />
                        )
                      })}
                    </div>
                  </div>
                </div>

                {/* Secondary Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <ScoreCard label="Facial Expression" score={report.analysis?.facial?.score || 0} icon={<Eye className="h-5 w-5" />} />
                  <ScoreCard label="Vocal Presence" score={report.analysis?.vocal?.score || 0} icon={<Volume2 className="h-5 w-5" />} />
                  <ScoreCard label="Content Quality" score={rescaleScore(report.analysis?.content?.score || 0)} icon={<Brain className="h-5 w-5" />} />
                </div>

                {/* Insight Cards */}
                {report.analysis?.coaching?.improvement_tips && report.analysis.coaching.improvement_tips.length > 0 && (
                  <div className="space-y-4">
                    <h5 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-amber-400" />
                      Key Insights to Improve
                    </h5>
                    <div className="grid grid-cols-1 gap-4">
                      {report.analysis.coaching.improvement_tips.slice(0, 3).map((tip: string, i: number) => {
                        let Icon = MessageSquare;
                        let colorClass = "bg-blue-500/10 text-blue-400";
                        let borderColor = "border-blue-500/20";
                        if (tip.toLowerCase().includes('star')) { Icon = BarChart3; colorClass = "bg-purple-500/10 text-purple-400"; borderColor = "border-purple-500/20"; }
                        else if (tip.toLowerCase().includes('impact')) { Icon = TrendingUp; colorClass = "bg-green-500/10 text-green-400"; borderColor = "border-green-500/20"; }
                        return (
                          <div key={i} className={cn("group flex gap-4 p-5 rounded-xl border transition-all hover:translate-x-1 bg-slate-800/20", borderColor)}>
                            <div className={cn("p-2.5 rounded-lg h-fit", colorClass)}><Icon className="h-5 w-5" /></div>
                            <div className="space-y-2 flex-1">
                              <div className="text-sm text-slate-200 leading-relaxed font-medium">
                                {tip.split(':').map((part: string, idx: number) => (idx === 0 ? <span key={idx} className="block text-white font-bold mb-1 text-base">{part}</span> : <span key={idx}>{part}</span>))}
                              </div>
                              <div className="flex gap-2 pt-2">
                                {tip.toLowerCase().includes('star') && <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase bg-white/5 hover:bg-white/10"><PlayCircle className="mr-1 h-3 w-3" /> See Example</Button>}
                                <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase text-indigo-400 hover:bg-indigo-500/10"><Sparkles className="mr-1 h-3 w-3" /> Fix This</Button>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Facial Tab */}
            {activeTab === 'facial' && report.analysis?.facial && (
              <div className="space-y-6 animate-in fade-in duration-500">
                <div className="p-6 rounded-xl bg-slate-800/20 border border-slate-700/50">
                  <h4 className="font-semibold mb-6 flex items-center gap-2 text-lg text-white">
                    <Eye className="h-5 w-5 text-accent" /> Facial Expression Metrics
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {Object.entries(report.analysis.facial.metrics || {}).map(([key, value]) => (
                      <MetricCard key={key} label={key} value={value as number} />
                    ))}
                  </div>

                  {/* Brief AI Coaching Tips */}
                  {report.analysis.coaching?.facial_tip && (
                    <div className="mt-8 space-y-4 pt-6 border-t border-slate-700/50">
                      <h5 className="text-sm font-semibold flex items-center gap-2 text-accent">
                        <Sparkles className="h-4 w-4" /> Facial Coaching
                      </h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <CoachingItem
                          type="facial"
                          text={report.analysis.coaching.facial_tip.what_went_well}
                          variant="success"
                        />
                        <CoachingItem
                          type="facial"
                          text={report.analysis.coaching.facial_tip.what_to_improve}
                          reason={report.analysis.coaching.facial_tip.reason}
                          variant="warning"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Vocal Tab */}
            {activeTab === 'voice' && report.analysis?.vocal && (
              <div className="space-y-6 animate-in fade-in duration-500">
                <div className="p-6 rounded-xl bg-slate-800/20 border border-slate-700/50">
                  <h4 className="font-semibold mb-6 flex items-center gap-2 text-lg text-white">
                    <Volume2 className="h-5 w-5 text-green-400" /> Vocal Presence Metrics
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {Object.entries(report.analysis.vocal.metrics || {}).map(([key, value]) => (
                      <MetricCard key={key} label={key} value={value as number} />
                    ))}
                  </div>

                  {/* Brief AI Coaching Tips */}
                  {report.analysis.coaching?.voice_tip && (
                    <div className="mt-8 space-y-4 pt-6 border-t border-slate-700/50">
                      <h5 className="text-sm font-semibold flex items-center gap-2 text-green-400">
                        <Sparkles className="h-4 w-4" /> Vocal Coaching
                      </h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <CoachingItem
                          type="voice"
                          text={report.analysis.coaching.voice_tip.what_went_well}
                          variant="success"
                        />
                        <CoachingItem
                          type="voice"
                          text={report.analysis.coaching.voice_tip.what_to_improve}
                          reason={report.analysis.coaching.voice_tip.reason}
                          variant="warning"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Content Tab */}
            {activeTab === 'content' && report.analysis?.content && (
              <div className="space-y-6 animate-in fade-in duration-500">
                {/* Advanced Score Normalization in Answer Quality Card */}
                {(() => {
                  const rawContentScore = report.analysis.coaching?.bert_score_f1 * 100 || report.analysis.text?.score || 0
                  const rescaledContentScore = rescaleScore(rawContentScore)
                  const verdictLabel = getScoreLabel(rescaledContentScore)

                  return (
                    <div className="p-6 rounded-xl bg-slate-800/40 border-2 border-slate-700/50 shadow-xl overflow-hidden relative group">
                      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Target className="w-24 h-24 text-blue-500" />
                      </div>

                      <div className="relative z-10 space-y-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-blue-500/20 rounded-lg">
                              <Brain className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                              <h3 className="text-lg font-bold text-white tracking-tight">Answer Quality Analysis</h3>
                              <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Semantic Similarity Verdict</p>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Badge variant={rescaledContentScore >= 90 ? 'success' : rescaledContentScore >= 70 ? 'info' : 'error'} className="px-3 py-1 font-bold shadow-lg">
                              {verdictLabel}
                            </Badge>
                            <StarRating rating={getStarRating(rescaledContentScore)} size="xs" />
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div className="flex justify-between items-center mb-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-slate-300">Rescaled Semantic Quality</span>
                              <Badge variant="ghost" className="text-[10px] bg-white/5 text-slate-500">Baseline 0.70</Badge>
                            </div>
                            <span className={cn("text-xl font-black", getScoreColor(rescaledContentScore))}>
                              {rescaledContentScore}%
                            </span>
                          </div>
                          <div className="h-3 w-full bg-slate-700/50 rounded-full overflow-hidden border border-slate-600/30 p-[2px]">
                            <div
                              className={cn("h-full rounded-full transition-all duration-1000 shadow-[0_0_15px_rgba(59,130,246,0.5)]", getScoreBg(rescaledContentScore))}
                              style={{ width: `${rescaledContentScore}%` }}
                            />
                          </div>
                        </div>

                        {report.analysis.text?.recommendations && report.analysis.text.recommendations.length > 0 && (
                          <div className="pt-4 border-t border-slate-700/30">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                              <Lightbulb className="w-4 h-4 text-amber-400" />
                              What could improve
                            </h4>
                            <ul className="space-y-2">
                              {report.analysis.text.recommendations.map((rec: any, idx: number) => (
                                <li key={idx} className="flex items-center gap-3 text-sm text-slate-300 group/item">
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50 group-hover/item:bg-blue-400 transition-colors" />
                                  {rec.text}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })()}

                <div className="p-6 rounded-xl bg-slate-800/20 border border-slate-700/50">
                  <h4 className="font-semibold mb-6 flex items-center gap-2 text-lg text-white">
                    <Brain className="h-5 w-5 text-purple-400" /> Content Metrics
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {Object.entries(report.analysis.content.metrics || {}).map(([key, value]) => (
                      <MetricCard key={key} label={key} value={value as number} />
                    ))}
                  </div>

                  {/* Brief AI Coaching Tips */}
                  {report.analysis.coaching?.content_tip && (
                    <div className="mt-8 space-y-4 pt-6 border-t border-slate-700/50">
                      <h5 className="text-sm font-semibold flex items-center gap-2 text-purple-400">
                        <Sparkles className="h-4 w-4" /> Content Coaching
                      </h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <CoachingItem
                          type="content"
                          text={report.analysis.coaching.content_tip.what_went_well}
                          variant="success"
                        />
                        <CoachingItem
                          type="content"
                          text={report.analysis.coaching.content_tip.what_to_improve}
                          reason={report.analysis.coaching.content_tip.reason}
                          variant="warning"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Detailed Analysis Tab */}
            {activeTab === 'detailed' && report.analysis?.coaching && (
              <div className="space-y-8 animate-in fade-in duration-500">
                <CompetencyRadarChart data={{
                  semanticAccuracy: rescaleScore(report.analysis.coaching.bert_score_f1 || 0),
                  qualityScore: (report.analysis.coaching.llm_judge_score || 5) * 10,
                  structureScore: report.analysis.coaching.star_breakdown ? (report.analysis.coaching.star_breakdown.situation + report.analysis.coaching.star_breakdown.task + report.analysis.coaching.star_breakdown.action + report.analysis.coaching.star_breakdown.result) / 4 : 50,
                  relevance: (report.analysis.coaching.content_relevance || 3) * 20,
                  coherence: (report.analysis.coaching.coherence_score || 3) * 20
                }} />
                {report.analysis.coaching.llm_judge_score !== undefined && (
                  <LLMJudgeFeedback score={report.analysis.coaching.llm_judge_score} rationale={report.analysis.coaching.llm_judge_rationale || ''} actionableTips={report.analysis.coaching.llm_actionable_tips} />
                )}
                {report.analysis.coaching.star_breakdown && (
                  <STARBreakdown breakdown={report.analysis.coaching.star_breakdown} contentRelevance={report.analysis.coaching.content_relevance} coherenceScore={report.analysis.coaching.coherence_score} />
                )}
              </div>
            )}

            {/* Common Items Section - Outside individual tab conditions but inside Tab Content container */}
            <div className="pt-8 border-t border-slate-800/50 space-y-6">
              {report.question && (
                <div className="p-4 rounded-lg bg-slate-800/20 border border-slate-700/30">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Session Question</span>
                  <p className="mt-1 font-medium text-slate-200">{report.question.text}</p>
                  <Badge variant="info" className="mt-2 text-[10px]">{report.question.category}</Badge>
                </div>
              )}
              {report.analysis?.transcript && (
                <div className="p-4 rounded-lg bg-slate-800/20 border border-slate-700/30">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Transcript Analysis</span>
                  <p className="mt-2 text-slate-300 text-sm leading-relaxed italic">"{report.analysis.transcript}"</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Emotion Timeline */}
      {report.emotionTimeline?.samples?.length > 0 && (
        <Card className="p-6 bg-slate-900/50 border-slate-800">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-white">
            <TrendingUp className="h-5 w-5 text-accent" /> Emotion Timeline
          </h2>
          <EmotionTimeline samples={report.emotionTimeline.samples} totalDuration={report.emotionTimeline.totalDuration} />
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4 justify-center pb-8">
        <Button asChild variant="secondary" className="px-8">
          <Link href="/practice">Practice Again</Link>
        </Button>
        <Button asChild variant="primary" className="px-8 bg-accent hover:bg-accent/90">
          <Link href="/reports">View All Reports</Link>
        </Button>
      </div>
    </div>
  )
}

// Helper Components

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'xs' | 'sm' | 'md' }) {
  const iconSize = size === 'xs' ? 'h-3 w-3' : size === 'sm' ? 'h-4 w-4' : 'h-6 w-6'
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          className={cn(
            iconSize,
            s <= rating ? "fill-amber-400 text-amber-400" : "fill-slate-700 text-slate-700"
          )}
        />
      ))}
    </div>
  )
}

function ScoreCard({ label, score, icon }: { label: string; score: number; icon: React.ReactNode }) {
  const getColor = (s: number) => {
    if (s >= 90) return 'text-green-400 border-green-500/30'
    if (s >= 50) return 'text-accent border-accent/30'
    return 'text-orange-400 border-orange-500/30'
  }

  const rating = getStarRating(score)

  return (
    <div className={cn(
      "text-center p-6 rounded-xl bg-background/50 border-2 transition-all hover:scale-105",
      getColor(score)
    )}>
      <div className="flex justify-center mb-2 opacity-60">{icon}</div>
      <div className="flex flex-col items-center gap-1">
        <p className={cn("text-3xl font-black", getColor(score).split(' ')[0])}>
          {score}%
        </p>
        <StarRating rating={rating} size="xs" />
      </div>
      <p className="text-[10px] uppercase font-bold text-foreground/40 mt-2 tracking-widest">{label}</p>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center p-4 rounded-lg bg-background/30 border border-border/30">
      <p className="text-2xl font-bold text-accent">{value}%</p>
      <p className="text-xs text-foreground/60 capitalize mt-1">
        {label.replace(/([A-Z])/g, ' $1').trim()}
      </p>
    </div>
  )
}

function CoachingItem({
  type,
  text,
  reason,
  variant
}: {
  type: 'content' | 'voice' | 'facial'
  text: string
  reason?: string
  variant: 'success' | 'warning'
}) {
  const iconColors = {
    content: 'bg-purple-500/20 text-purple-400',
    voice: 'bg-green-500/20 text-green-400',
    facial: 'bg-blue-500/20 text-blue-400',
  }

  const icons = {
    content: <MessageSquare className="h-4 w-4" />,
    voice: <Volume2 className="h-4 w-4" />,
    facial: <Eye className="h-4 w-4" />,
  }

  const bgColors = {
    success: 'bg-green-500/10 border-green-500/20',
    warning: 'bg-yellow-500/10 border-yellow-500/20',
  }

  return (
    <div className={cn("flex items-start gap-3 p-3 rounded-lg border", bgColors[variant])}>
      <div className={cn("p-1.5 rounded-lg", iconColors[type])}>
        {icons[type]}
      </div>
      <div className="flex-1">
        <p className="text-sm text-foreground/80">{text}</p>
        {reason && (
          <p className="text-xs text-foreground/50 mt-1">{reason}</p>
        )}
      </div>
    </div>
  )
}
