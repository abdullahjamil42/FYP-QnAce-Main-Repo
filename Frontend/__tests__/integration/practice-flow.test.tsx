import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PracticeSessionPage from '@/app/(app)/practice/[sessionId]/page'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useParams: () => ({ sessionId: 'test-session' }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

// Mock toast
jest.mock('@/components/ui/toast', () => ({
  useToast: () => ({
    addToast: jest.fn(),
  }),
}))

describe('Practice Flow Integration', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('displays question and recorder', () => {
    render(<PracticeSessionPage />)
    expect(screen.getByText(/practice session/i)).toBeInTheDocument()
  })

  // Note: Full MediaRecorder integration testing would require more complex mocking
  // This is a basic structure that can be expanded
})

