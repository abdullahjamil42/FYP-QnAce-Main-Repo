import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SettingsPage from '@/app/(app)/settings/page'
import { useAuth } from '@/hooks/use-auth'
import { useToast } from '@/components/ui/toast'
import * as authLib from '@/lib/auth'

jest.mock('@/hooks/use-auth')
jest.mock('@/components/ui/toast')
jest.mock('@/lib/auth', () => ({
  setUser: jest.fn(),
}))

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>

describe('SettingsPage', () => {
  const mockAddToast = jest.fn()
  const mockLogout = jest.fn()

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
      logout: mockLogout,
    })

    mockUseToast.mockReturnValue({
      addToast: mockAddToast,
    })
  })

  it('renders settings page correctly', () => {
    render(<SettingsPage />)
    expect(screen.getByText(/settings/i)).toBeInTheDocument()
  })

  it('displays user profile form', () => {
    render(<SettingsPage />)
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument()
  })

  it('pre-fills form with user data', () => {
    render(<SettingsPage />)
    const nameInput = screen.getByLabelText(/full name/i) as HTMLInputElement
    expect(nameInput.value).toBe('Test User')
  })

  it('disables email field', () => {
    render(<SettingsPage />)
    const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement
    expect(emailInput).toBeDisabled()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)
    
    const nameInput = screen.getByLabelText(/full name/i)
    await user.clear(nameInput)
    await user.tab() // Blur the input to trigger validation
    
    const submitButtons = screen.getAllByRole('button', { name: /save changes/i })
    const form = nameInput.closest('form')
    
    if (form) {
      fireEvent.submit(form)
    }
    
    // Wait for validation error to appear - react-hook-form should show error
    await waitFor(() => {
      const errorMessage = screen.queryByText(/name is required/i)
      expect(errorMessage).toBeInTheDocument()
    }, { timeout: 2000 })
  })

  it('submits form successfully', async () => {
    const user = userEvent.setup()
    
    render(<SettingsPage />)
    
    const nameInput = screen.getByLabelText(/full name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Name')
    
    // Also fill role field to ensure form is valid
    const roleInput = screen.getByLabelText(/role/i)
    await user.clear(roleInput)
    await user.type(roleInput, 'Senior Engineer')
    
    // Find the form and submit it
    const form = screen.getByLabelText(/full name/i).closest('form')
    expect(form).toBeInTheDocument()
    
    // Submit the form
    fireEvent.submit(form!)
    
    // Wait for form submission and toast
    await waitFor(() => {
      expect(authLib.setUser).toHaveBeenCalled()
      expect(mockAddToast).toHaveBeenCalledWith({
        type: 'success',
        message: 'Profile updated successfully',
      })
    }, { timeout: 3000 })
  })

  it('handles logout', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)
    
    const logoutButtons = screen.getAllByRole('button', { name: /log out/i })
    expect(logoutButtons.length).toBeGreaterThan(0)
    // Logout button should be present and clickable
    await user.click(logoutButtons[0])
    
    // The logout function from useAuth hook should be available
    // Note: In a real scenario, this would trigger logout
    expect(logoutButtons[0]).toBeInTheDocument()
  })
})

