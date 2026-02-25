'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

import Link from 'next/link'
import { FileText, Calendar } from 'lucide-react'

export default function ReportsPage() {
  const [reports, setReports] = React.useState<Array<{
    id: string
    sessionId: string
    overallScore: number
    createdAt: string
  }>>([])

  React.useEffect(() => {
    // Load reports from localStorage
    const storedReports = JSON.parse(localStorage.getItem('qace_reports') || '[]')
    setReports(
      storedReports.map((report: any) => ({
        id: report.id,
        sessionId: report.sessionId,
        overallScore: report.analysis.overallScore,
        createdAt: report.createdAt,
      }))
    )
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Reports</h1>
          <p className="text-foreground/60">View your practice session analysis</p>
        </div>
      </div>

      {reports.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-foreground/40 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Reports Yet</h3>
            <p className="text-foreground/60 mb-4">
              Complete a practice session to see your analysis reports here.
            </p>
            <Button asChild variant="primary">
              <Link href="/practice">Start Practicing</Link>
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <Card key={report.id} hoverable>
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold mb-1">Practice Session</h3>
                    <div className="flex items-center gap-2 text-sm text-foreground/60">
                      <Calendar className="h-4 w-4" />
                      {new Date(report.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <Badge
                    variant={
                      report.overallScore >= 80
                        ? 'success'
                        : report.overallScore >= 70
                          ? 'info'
                          : 'warning'
                    }
                  >
                    {report.overallScore}%
                  </Badge>
                </div>
                <Button asChild variant="primary" className="w-full">
                  <Link href={`/reports/${report.id}`}>View Report</Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

