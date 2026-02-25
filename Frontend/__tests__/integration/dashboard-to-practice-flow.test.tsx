import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DashboardPage from '@/app/(app)/dashboard/page'
import { useAuth } from '@/hooks/use-auth'

jest.mock('@/hooks/use-auth')
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>

describe('Dashboard to Practice Flow', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'Software Engineer',
        experienceLevel: 'mid',
        interviewTypes: [],
        goals: {},
        createdAt: new Date().toISOString(),
      },
      loading: false,
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
    })
  })

  it('navigates to practice from dashboard', async () => {
    const user = userEvent.setup()
    render(<DashboardPage />)

    const practiceButton = screen.getByRole('link', { name: /start new practice session/i })
    expect(practiceButton).toBeInTheDocument()
    expect(practiceButton).toHaveAttribute('href', '/practice')
  })

  it('navigates to reports from dashboard', () => {
    render(<DashboardPage />)

    const reportsButton = screen.getByRole('link', { name: /view latest report/i })
    expect(reportsButton).toBeInTheDocument()
    expect(reportsButton).toHaveAttribute('href', '/reports')
  })
})

