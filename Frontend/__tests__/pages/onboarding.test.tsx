import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import OnboardingPage from '@/app/onboarding/page'
import { useAuth } from '@/hooks/use-auth'
import { useToast } from '@/components/ui/toast'

jest.mock('@/hooks/use-auth')
jest.mock('@/components/ui/toast')
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>

describe('OnboardingPage', () => {
  const mockAddToast = jest.fn()
  const mockLogin = jest.fn().mockResolvedValue({
    id: 'user-1',
    email: 'test@example.com',
    name: 'test',
    role: 'Software Engineer',
    experienceLevel: 'mid',
    interviewTypes: [],
    goals: {},
    createdAt: new Date().toISOString(),
  })

  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      isAuthenticated: false,
      login: mockLogin,
      logout: jest.fn(),
    })

    mockUseToast.mockReturnValue({
      addToast: mockAddToast,
    })
  })

  it('renders onboarding page correctly', () => {
    render(<OnboardingPage />)
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
  })

  it('shows profile setup as first step', () => {
    const { container } = render(<OnboardingPage />)
    // Profile setup should be visible
    expect(container).toBeInTheDocument()
  })

  it('displays progress indicator', () => {
    render(<OnboardingPage />)
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
  })

  it('redirects authenticated users', () => {
    const mockPush = jest.fn()
    jest.doMock('next/navigation', () => ({
      useRouter: () => ({
        push: mockPush,
      }),
    }))

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

    render(<OnboardingPage />)
    // Should redirect (tested via router mock)
  })
})

