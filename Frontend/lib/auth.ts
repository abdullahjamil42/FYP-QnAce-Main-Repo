import { User } from './mock-data'

export interface SignupData {
  email: string
  password: string
  name: string
}

export interface AuthResult {
  success: boolean
  user?: User
  error?: string
}

const STORAGE_KEY = 'qnace_user'
const ONBOARDING_KEY = 'qnace_onboarding_complete'

export function getUser(): User | null {
  if (typeof window === 'undefined') return null
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return null
  try {
    return JSON.parse(stored)
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  return getUser() !== null
}

export async function login(email: string, password: string): Promise<AuthResult> {
  await new Promise(r => setTimeout(r, 500))
  if (!email || !password) {
    return { success: false, error: 'Email and password required' }
  }
  const user: User = {
    id: '1',
    email,
    name: email.split('@')[0],
    createdAt: new Date().toISOString()
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
  return { success: true, user }
}

export async function signup(data: SignupData): Promise<AuthResult> {
  await new Promise(r => setTimeout(r, 500))
  if (!data.email || !data.password || !data.name) {
    return { success: false, error: 'All fields required' }
  }
  return { success: true }
}

export function logout(): void {
  localStorage.removeItem(STORAGE_KEY)
  localStorage.removeItem(ONBOARDING_KEY)
}

export function hasCompletedOnboarding(): boolean {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(ONBOARDING_KEY) === 'true'
}

export function completeOnboarding(profileData: Partial<User>): void {
  const user = getUser()
  if (user) {
    const updated = { ...user, ...profileData }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  }
  localStorage.setItem(ONBOARDING_KEY, 'true')
}