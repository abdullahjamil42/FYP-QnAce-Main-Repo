'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BookOpen, ExternalLink, Video, FileText, Code } from 'lucide-react'

const resources = [
  {
    title: 'Interview Best Practices',
    description: 'Learn the fundamentals of successful interviews from Indeed',
    category: 'Guide',
    icon: BookOpen,
    url: 'https://www.indeed.com/career-advice/interviewing',
  },
  {
    title: 'STAR Method Explained',
    description: 'Master the Situation-Task-Action-Result framework',
    category: 'Method',
    icon: FileText,
    url: 'https://www.themuse.com/advice/star-interview-method',
  },
  {
    title: 'System Design Fundamentals',
    description: 'Essential concepts for system design interviews',
    category: 'Technical',
    icon: Code,
    url: 'https://github.com/donnemartin/system-design-primer',
  },
  {
    title: 'Behavioral Questions Database',
    description: 'Common behavioral questions and how to answer them',
    category: 'Database',
    icon: FileText,
    url: 'https://www.glassdoor.com/blog/common-interview-questions/',
  },
  {
    title: 'LeetCode Practice',
    description: 'Practice coding problems for technical interviews',
    category: 'Technical',
    icon: Code,
    url: 'https://leetcode.com/',
  },
  {
    title: 'Mock Interview Videos',
    description: 'Watch real mock interviews on YouTube',
    category: 'Video',
    icon: Video,
    url: 'https://www.youtube.com/results?search_query=mock+interview',
  },
]

export default function ResourcesPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Resources</h1>
        <p className="text-foreground/60">Helpful guides and materials for interview preparation</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {resources.map((resource, index) => {
          const Icon = resource.icon
          return (
            <Card key={index} hoverable>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-accent/10">
                    <Icon className="h-5 w-5 text-accent" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold mb-1">{resource.title}</h3>
                    <p className="text-sm text-foreground/60">{resource.description}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground/40">{resource.category}</span>
                  <Button asChild variant="ghost" size="sm">
                    <a href={resource.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Open
                    </a>
                  </Button>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

