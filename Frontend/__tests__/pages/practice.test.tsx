import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PracticePage from '@/app/(app)/practice/page'
import { useAuth } from '@/hooks/use-auth'

jest.mock('@/hooks/use-auth')
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

// Mock window.location
delete (window as any).location
window.location = { href: '' } as any

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>

describe('PracticePage', () => {
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

  it('renders practice page correctly', () => {
    render(<PracticePage />)
    expect(screen.getByText(/practice sessions/i)).toBeInTheDocument()
  })

  it('displays new session button', () => {
    render(<PracticePage />)
    const newSessionButton = screen.getByRole('button', { name: /new session/i })
    expect(newSessionButton).toBeInTheDocument()
  })

  it('displays practice sessions', async () => {
    render(<PracticePage />)
    await waitFor(() => {
      expect(screen.getAllByText(/completed|pending/i).length).toBeGreaterThan(0)
    })
  })

  it('creates new session when button is clicked', async () => {
    const user = userEvent.setup()
    render(<PracticePage />)
    
    const newSessionButton = screen.getByRole('button', { name: /new session/i })
    await user.click(newSessionButton)
    
    // Should navigate to new session
    await waitFor(() => {
      expect(window.location.href).toContain('/practice/')
    })
  })

  it('shows session cards with correct information', async () => {
    render(<PracticePage />)
    await waitFor(() => {
      const sessionCards = screen.getAllByText(/completed|pending/i)
      expect(sessionCards.length).toBeGreaterThan(0)
    })
  })
})

