'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Briefcase, MapPin, ExternalLink, Search } from 'lucide-react'

const jobs = [
  {
    title: 'Senior Software Engineer',
    company: 'Google',
    location: 'Mountain View, CA',
    type: 'Full-time',
    match: 85,
    url: 'https://careers.google.com/jobs/',
  },
  {
    title: 'Full Stack Developer',
    company: 'Meta',
    location: 'Remote',
    type: 'Full-time',
    match: 78,
    url: 'https://www.metacareers.com/',
  },
  {
    title: 'Backend Engineer',
    company: 'Amazon',
    location: 'Seattle, WA',
    type: 'Full-time',
    match: 92,
    url: 'https://www.amazon.jobs/',
  },
  {
    title: 'Software Development Engineer',
    company: 'Microsoft',
    location: 'Redmond, WA',
    type: 'Full-time',
    match: 88,
    url: 'https://careers.microsoft.com/',
  },
  {
    title: 'Frontend Engineer',
    company: 'Apple',
    location: 'Cupertino, CA',
    type: 'Full-time',
    match: 75,
    url: 'https://www.apple.com/careers/',
  },
]

export default function JobsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Job Opportunities</h1>
        <p className="text-foreground/60">Discover roles that match your profile and practice for them</p>
      </div>

      <Card className="bg-accent/10 border-accent/20">
        <div className="flex items-center gap-3">
          <Search className="h-5 w-5 text-accent" />
          <div>
            <p className="font-medium">Pro Tip</p>
            <p className="text-sm text-foreground/60">Practice with questions tailored to your target companies to increase your chances!</p>
          </div>
        </div>
      </Card>

      <div className="space-y-4">
        {jobs.map((job, index) => (
          <Card key={index} hoverable>
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-3">
                <div>
                  <h3 className="text-xl font-semibold mb-1">{job.title}</h3>
                  <div className="flex items-center gap-4 text-sm text-foreground/60">
                    <div className="flex items-center gap-1">
                      <Briefcase className="h-4 w-4" />
                      {job.company}
                    </div>
                    <div className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {job.location}
                    </div>
                    <span>{job.type}</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-3">
                <Badge variant={job.match >= 85 ? 'success' : job.match >= 75 ? 'info' : 'default'}>
                  {job.match}% Match
                </Badge>
                <Button asChild variant="ghost" size="sm">
                  <a href={job.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Jobs
                  </a>
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

