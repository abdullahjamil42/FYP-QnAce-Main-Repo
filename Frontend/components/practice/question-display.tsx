'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Question } from '@/lib/mock-data'

export interface QuestionDisplayProps {
  question: Question
}

export function QuestionDisplay({ question }: QuestionDisplayProps) {
  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Badge variant="info">{question.category}</Badge>
          <Badge variant="default">{question.difficulty}</Badge>
        </div>
        <h2 className="text-2xl font-semibold">{question.text}</h2>
        <div className="flex flex-wrap gap-2">
          {question.tags.map((tag) => (
            <Badge key={tag} variant="default" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </div>
    </Card>
  )
}

