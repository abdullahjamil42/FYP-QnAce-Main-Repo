import { render, screen, waitFor } from '@testing-library/react'
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

describe('DashboardPage', () => {
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

  it('renders dashboard with user greeting', () => {
    render(<DashboardPage />)
    expect(screen.getByText(/welcome back, test user!/i)).toBeInTheDocument()
  })

  it('displays stats cards', () => {
    render(<DashboardPage />)
    expect(screen.getAllByText(/practice sessions/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/average score/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/goals completed/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/time practiced/i).length).toBeGreaterThan(0)
  })

  it('displays quick actions', () => {
    render(<DashboardPage />)
    expect(screen.getByText(/start new practice session/i)).toBeInTheDocument()
    expect(screen.getByText(/view latest report/i)).toBeInTheDocument()
  })

  it('displays recent sessions', () => {
    render(<DashboardPage />)
    expect(screen.getByText(/recent practice sessions/i)).toBeInTheDocument()
  })

  it('shows progress overview', () => {
    render(<DashboardPage />)
    expect(screen.getByText(/progress overview/i)).toBeInTheDocument()
    expect(screen.getByText(/overall score/i)).toBeInTheDocument()
  })

  it('handles loading state', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: true,
      isAuthenticated: false,
      login: jest.fn(),
      logout: jest.fn(),
    })
    render(<DashboardPage />)
    // Component should still render - check for dashboard content
    expect(screen.getByText(/welcome back/i) || screen.getByText(/practice sessions/i)).toBeTruthy()
  })
})

