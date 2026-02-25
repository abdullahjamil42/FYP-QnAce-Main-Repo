# Q&Ace - AI-Powered Interview Preparation Platform

Q&Ace is a premium, full-stack Next.js application that provides AI-powered multi-modal feedback for interview preparation. The platform offers facial analysis, voice/tone analysis, and NLP evaluation to help professionals prepare for high-stakes interviews.

## Features

- 🎯 **Multi-Modal Analysis**: Get feedback on facial expressions, voice tone, and content quality
- 🎥 **Browser-Based Recording**: Record practice sessions directly in your browser
- 📊 **Detailed Reports**: Comprehensive three-column analysis with progress tracking
- 🎨 **Premium Design**: Dark-themed gradient system with smooth animations
- ♿ **Accessible**: WCAG AA compliant with keyboard navigation and reduced-motion support
- 📱 **Responsive**: Works seamlessly on desktop, tablet, and mobile devices

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS with CSS variables
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Forms**: React Hook Form
- **Testing**: Jest, React Testing Library, jest-axe
- **Component Development**: Storybook

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Modern browser with MediaRecorder API support

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Shamil
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm test` - Run tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Generate test coverage report
- `npm run storybook` - Start Storybook
- `npm run build-storybook` - Build Storybook for deployment

## Project Structure

```
/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Marketing landing page
│   ├── onboarding/       # Onboarding flow
│   ├── (app)/             # Authenticated app shell
│   │   ├── dashboard/     # Dashboard page
│   │   ├── practice/      # Practice sessions
│   │   ├── reports/       # Analysis reports
│   │   ├── resources/     # Resources page
│   │   ├── jobs/          # Jobs page
│   │   └── settings/      # Settings page
│   └── (admin)/           # Admin interface
│       └── admin/         # Question bank management
├── components/            # React components
│   ├── ui/                # Reusable UI components
│   ├── marketing/         # Marketing page components
│   ├── onboarding/       # Onboarding components
│   ├── practice/          # Practice session components
│   └── reports/           # Report visualization components
├── lib/                   # Utility functions and data
│   ├── auth.ts           # Authentication utilities
│   ├── mock-data.ts      # Mock data structures
│   └── utils.ts          # General utilities
├── hooks/                 # Custom React hooks
├── styles/                # Global styles and CSS variables
├── stories/              # Storybook stories
├── __tests__/            # Test files
└── public/               # Static assets
```

## Mock Data Structures

### User

```typescript
interface User {
  id: string
  email: string
  name: string
  role: string
  experienceLevel: 'entry' | 'mid' | 'senior' | 'executive'
  interviewTypes: string[]
  goals: {
    targetCompanies?: string[]
    timeline?: string
    focusAreas?: string[]
  }
  createdAt: string
}
```

### Practice Session

```typescript
interface PracticeSession {
  id: string
  userId: string
  questionId: string
  question: {
    id: string
    text: string
    category: string
    difficulty: 'easy' | 'medium' | 'hard'
  }
  recordingUrl?: string
  status: 'pending' | 'recording' | 'analyzing' | 'completed' | 'failed'
  createdAt: string
  completedAt?: string
}
```

### Analysis Result

```typescript
interface AnalysisResult {
  facial: {
    score: number
    metrics: {
      eyeContact: number
      posture: number
      expressions: number
      confidence: number
    }
    recommendations: Recommendation[]
  }
  vocal: {
    score: number
    metrics: {
      tone: number
      pace: number
      clarity: number
      volume: number
    }
    recommendations: Recommendation[]
  }
  content: {
    score: number
    metrics: {
      structure: number
      relevance: number
      keywords: number
      completeness: number
    }
    recommendations: Recommendation[]
  }
  transcript: string
  keywords: string[]
  overallScore: number
}
```

### Report

```typescript
interface Report {
  id: string
  sessionId: string
  userId: string
  analysis: AnalysisResult
  createdAt: string
  progress?: {
    facial: number[]
    vocal: number[]
    content: number[]
    dates: string[]
  }
}
```

## API Response Formats (Future Backend Integration)

### Authentication

**POST /api/auth/login**
```json
{
  "user": {
    "id": "user-1",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "Software Engineer",
    "experienceLevel": "mid",
    "interviewTypes": ["technical", "behavioral"],
    "goals": {
      "targetCompanies": ["Google", "Meta"],
      "timeline": "3 months",
      "focusAreas": ["System Design"]
    }
  },
  "token": "jwt-token-here"
}
```

### Practice Sessions

**POST /api/sessions**
```json
{
  "session": {
    "id": "session-123",
    "userId": "user-1",
    "questionId": "q-1",
    "status": "pending",
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

**POST /api/sessions/:id/recordings**
- Content-Type: `multipart/form-data`
- Body: Video/audio blob file

### Analysis

**POST /api/sessions/:id/analyze**
```json
{
  "analysis": {
    "facial": { /* AnalysisResult.facial */ },
    "vocal": { /* AnalysisResult.vocal */ },
    "content": { /* AnalysisResult.content */ },
    "transcript": "Full transcript text...",
    "keywords": ["keyword1", "keyword2"],
    "overallScore": 78
  },
  "reportId": "report-123"
}
```

### Reports

**GET /api/reports/:id**
```json
{
  "report": {
    "id": "report-123",
    "sessionId": "session-123",
    "userId": "user-1",
    "analysis": { /* AnalysisResult */ },
    "createdAt": "2024-01-01T00:00:00Z",
    "progress": {
      "facial": [65, 70, 72, 75, 78],
      "vocal": [80, 82, 83, 84, 85],
      "content": [68, 70, 71, 72, 72],
      "dates": ["2024-01-01T00:00:00Z", "..."]
    }
  }
}
```

## Visual System

### Colors

- **Primary Dark**: `#0b0f17`
- **Gradient Purple**: `#1a0b2e`
- **Gradient Blue**: `#16213e`
- **Gradient Teal**: `#0f3460`
- **Accent Teal**: `#00d9ff`
- **Accent Purple**: `#a855f7`

### Typography

- **Font Family**: Inter (system fallback)
- **Weights**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

### Spacing

- **Baseline**: 8px
- **Grid**: 12-column responsive grid

### Motion Durations

- **Micro-interactions**: 80-220ms
- **Reveals**: 300-550ms
- **Reduced Motion**: All animations respect `prefers-reduced-motion`

## Accessibility

Q&Ace is built with accessibility in mind:

- ✅ WCAG AA compliant
- ✅ Keyboard navigation throughout
- ✅ Semantic HTML elements
- ✅ ARIA labels and descriptions
- ✅ Focus management
- ✅ Color contrast ratios ≥4.5:1
- ✅ Reduced motion support
- ✅ Screen reader compatible

## Performance

### Performance Budgets

- **First Contentful Paint (FCP)**: < 1.8s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Time to Interactive (TTI)**: < 3.8s
- **Total Blocking Time (TBT)**: < 200ms
- **Cumulative Layout Shift (CLS)**: < 0.1

### Optimization Strategies

- Code splitting (route-based and component-based)
- Lazy loading for non-critical components
- Optimized images (AVIF/WebP)
- Tree-shaking for unused code
- Bundle size monitoring

### Lighthouse Targets

- **Performance**: > 90
- **Accessibility**: > 90
- **Best Practices**: > 90
- **SEO**: > 90

## Testing

### Unit Tests

Run unit tests for components:
```bash
npm test
```

### Integration Tests

Test complete user flows:
```bash
npm test -- --testPathPattern=integration
```

### Accessibility Tests

All components are tested with jest-axe:
```bash
npm test -- --testPathPattern=components
```

### Coverage

Generate coverage report:
```bash
npm run test:coverage
```

## Storybook

View and interact with all UI components:

```bash
npm run storybook
```

Stories are available for:
- Button (all variants and states)
- Card (hoverable and static)
- Badge (all variants)
- Modal
- Toast
- Chart (Sparkline and Gauge)
- MediaRecorder

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Configure environment variables (if needed)
4. Deploy

The project is configured for Vercel deployment out of the box.

### Environment Variables

Currently, no environment variables are required as the app uses mock data. For production backend integration, you may need:

```env
NEXT_PUBLIC_API_URL=https://api.qace.com
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

## Demo Mode

The marketing landing page includes a demo mode that cycles through mock session snippets without requiring actual recording. This allows for easy demonstrations without browser permissions.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- MediaRecorder API required for recording functionality

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass
6. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.

---

Built with ❤️ using Next.js, TypeScript, and Tailwind CSS

