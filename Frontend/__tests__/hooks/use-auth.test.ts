import { renderHook, act, waitFor } from '@testing-library/react'
import { useAuth } from '@/hooks/use-auth'
import * as authLib from '@/lib/auth'

jest.mock('@/lib/auth')

const mockAuthLib = authLib as jest.Mocked<typeof authLib>

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('initializes with user from localStorage', () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'Software Engineer',
      experienceLevel: 'mid',
      interviewTypes: [],
      goals: {},
      createdAt: new Date().toISOString(),
    }

    mockAuthLib.getUser.mockReturnValue(mockUser)
    mockAuthLib.isAuthenticated.mockReturnValue(true)

    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.loading).toBe(false)
  })

  it('initializes with null user when not authenticated', () => {
    mockAuthLib.getUser.mockReturnValue(null)
    mockAuthLib.isAuthenticated.mockReturnValue(false)

    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.loading).toBe(false)
  })

  it('handles login', async () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'Software Engineer',
      experienceLevel: 'mid',
      interviewTypes: [],
      goals: {},
      createdAt: new Date().toISOString(),
    }

    mockAuthLib.getUser.mockReturnValue(null)
    mockAuthLib.isAuthenticated.mockReturnValue(false)
    mockAuthLib.login.mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.login('test@example.com')
    })

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })
    expect(mockAuthLib.login).toHaveBeenCalledWith('test@example.com', undefined)
  })

  it('handles logout', () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'Software Engineer',
      experienceLevel: 'mid',
      interviewTypes: [],
      goals: {},
      createdAt: new Date().toISOString(),
    }

    mockAuthLib.getUser.mockReturnValue(mockUser)
    mockAuthLib.isAuthenticated.mockReturnValue(true)

    const { result } = renderHook(() => useAuth())

    act(() => {
      result.current.logout()
    })

    expect(mockAuthLib.logout).toHaveBeenCalled()
    expect(result.current.user).toBeNull()
  })
})

