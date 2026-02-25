'use client'

import * as React from 'react'
import { Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'
import { useToast } from '@/components/ui/toast'
import { 
  Loader2, 
  Mail, 
  Lock, 
  User, 
  ArrowRight, 
  Check,
  Sparkles,
  ArrowLeft
} from 'lucide-react'

function AuthForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, signup, isAuthenticated, needsOnboarding } = useAuth()
  const { addToast } = useToast()

  // Check if signup mode is requested via URL
  const modeFromUrl = searchParams.get('mode')
  const [isLoginMode, setIsLoginMode] = React.useState(modeFromUrl !== 'signup')
  const [name, setName] = React.useState('')
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState('')

  // Redirect if already logged in
  React.useEffect(() => {
    if (isAuthenticated) {
      if (needsOnboarding) {
        router.push('/onboarding')
      } else {
        router.push('/dashboard')
      }
    }
  }, [isAuthenticated, needsOnboarding, router])

  // Clear error when switching modes
  React.useEffect(() => {
    setError('')
  }, [isLoginMode])

  const passwordRequirements = [
    { met: password.length >= 6, text: 'At least 6 characters' },
    { met: password === confirmPassword && password.length > 0, text: 'Passwords match' },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      if (isLoginMode) {
        const result = await login(email, password)
        
        if (result.success) {
          addToast({
            type: 'success',
            message: `Welcome back, ${result.user?.name}!`,
          })
          
          const redirectTo = searchParams.get('redirect') || (result.isNewUser ? '/onboarding' : '/dashboard')
          router.push(redirectTo)
        } else {
          setError(result.error || 'Login failed')
        }
      } else {
        if (password.length < 6) {
          setError('Password must be at least 6 characters')
          setIsLoading(false)
          return
        }

        if (password !== confirmPassword) {
          setError('Passwords do not match')
          setIsLoading(false)
          return
        }

        const result = await signup({ email, password, name })
        
        if (result.success) {
          addToast({
            type: 'success',
            message: `Account created successfully! Please log in.`,
          })
          // Switch to login mode and clear form
          setIsLoginMode(true)
          setName('')
          setPassword('')
          setConfirmPassword('')
          // Keep email for convenience
        } else {
          setError(result.error || 'Signup failed')
        }
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Header */}
      <header className="p-6 flex items-center justify-between">
        <Link href="/" className="inline-flex items-center gap-2 text-xl font-bold group">
          <div className="relative">
            <div className="absolute inset-0 bg-accent/20 blur-lg rounded-full group-hover:bg-accent/30 transition-colors" />
            <Sparkles className="h-6 w-6 text-accent relative" />
          </div>
          <span className="gradient-text">Q&Ace</span>
        </Link>
        <Link 
          href="/"
          className="flex items-center gap-2 text-foreground/60 hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Home
        </Link>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          <Card hoverable={false} className="border-foreground/10 bg-card/60 backdrop-blur-md p-8 relative overflow-hidden">
            {/* Subtle gradient orbs in background */}
            <div className="absolute -top-24 -right-24 w-48 h-48 bg-accent/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-accent-purple/10 rounded-full blur-3xl pointer-events-none" />
            
            {/* Toggle */}
            <div className="relative mb-8">
              <div className="group relative flex rounded-full border border-foreground/20 overflow-hidden h-12 cursor-pointer">
                {/* Active pill background */}
                <motion.div
                  className="absolute inset-y-0 w-1/2 bg-accent rounded-full transition-shadow duration-300 group-hover:shadow-[0_0_30px_rgba(0,217,255,0.6)]"
                  initial={false}
                  animate={{ x: isLoginMode ? 0 : '100%' }}
                  transition={{ 
                    type: 'tween',
                    ease: [0.4, 0, 0.2, 1],
                    duration: 0.3
                  }}
                />
                <button
                  type="button"
                  onClick={() => setIsLoginMode(true)}
                  className={`relative z-10 flex-1 text-sm font-semibold transition-colors duration-300 ${
                    isLoginMode 
                      ? 'text-background' 
                      : 'text-foreground/60 hover:text-foreground'
                  }`}
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => setIsLoginMode(false)}
                  className={`relative z-10 flex-1 text-sm font-semibold transition-colors duration-300 ${
                    !isLoginMode 
                      ? 'text-background' 
                      : 'text-foreground/60 hover:text-foreground'
                  }`}
                >
                  Signup
                </button>
              </div>
            </div>

            {/* Header */}
            <AnimatePresence mode="wait">
              <motion.div
                key={isLoginMode ? 'login-header' : 'signup-header'}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="text-center mb-8"
              >
                <h1 className="text-2xl font-bold mb-2 bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text">
                  {isLoginMode ? 'Welcome Back' : 'Create Your Account'}
                </h1>
                <p className="text-foreground/50 text-sm">
                  {isLoginMode 
                    ? 'Sign in to continue your interview practice' 
                    : 'Start mastering your interview skills today'}
                </p>
              </motion.div>
            </AnimatePresence>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <AnimatePresence mode="wait">
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence mode="wait">
                <motion.div
                  key={isLoginMode ? 'login-form' : 'signup-form'}
                  initial={{ opacity: 0, x: isLoginMode ? -20 : 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: isLoginMode ? 20 : -20 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-4"
                >
                  {/* Name field (signup only) */}
                  {!isLoginMode && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="space-y-2"
                    >
                      <Label htmlFor="name">Full Name</Label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground/40" />
                        <Input
                          id="name"
                          type="text"
                          placeholder="John Doe"
                          value={name}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                          className="pl-10"
                          required={!isLoginMode}
                          disabled={isLoading}
                        />
                      </div>
                    </motion.div>
                  )}

                  {/* Email field */}
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground/40" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                        className="pl-10"
                        required
                        disabled={isLoading}
                      />
                    </div>
                  </div>

                  {/* Password field */}
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground/40" />
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                        className="pl-10"
                        required
                        disabled={isLoading}
                      />
                    </div>
                  </div>

                  {/* Confirm Password (signup only) */}
                  {!isLoginMode && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="space-y-2"
                    >
                      <Label htmlFor="confirmPassword">Confirm Password</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground/40" />
                        <Input
                          id="confirmPassword"
                          type="password"
                          placeholder="••••••••"
                          value={confirmPassword}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
                          className="pl-10"
                          required={!isLoginMode}
                          disabled={isLoading}
                        />
                      </div>
                    </motion.div>
                  )}

                  {/* Password requirements (signup only) */}
                  {!isLoginMode && password.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex flex-wrap gap-3 pt-2"
                    >
                      {passwordRequirements.map((req, index) => (
                        <motion.div 
                          key={index}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: index * 0.1 }}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
                            req.met 
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                              : 'bg-foreground/5 text-foreground/50 border border-foreground/10'
                          }`}
                        >
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                          >
                            <Check className={`h-3 w-3 ${req.met ? 'opacity-100' : 'opacity-40'}`} />
                          </motion.div>
                          {req.text}
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </motion.div>
              </AnimatePresence>

              {/* Submit button */}
              <motion.div
                whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(0, 217, 255, 0.3)' }}
                whileTap={{ scale: 0.98 }}
                className="pt-2"
              >
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full py-3 text-base font-semibold relative overflow-hidden group"
                  disabled={isLoading || (!isLoginMode && !passwordRequirements.every(r => r.met))}
                >
                  <span className="relative z-10 flex items-center justify-center">
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        {isLoginMode ? 'Signing in...' : 'Creating account...'}
                      </>
                    ) : (
                      <>
                        {isLoginMode ? 'Sign In' : 'Create Account'}
                        <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </span>
                </Button>
              </motion.div>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full h-px bg-foreground/10" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-6 py-1.5 text-sm text-foreground/50 bg-card rounded-full">
                  or
                </span>
              </div>
            </div>

            {/* Demo link */}
            <motion.button
              whileHover={{ 
                scale: 1.01,
                boxShadow: '0 0 30px rgba(0,217,255,0.4), 0 0 60px rgba(0,217,255,0.2)'
              }}
              whileTap={{ scale: 0.99 }}
              type="button"
              onClick={() => router.push('/demo')}
              className="group w-full py-3.5 px-6 rounded-full text-foreground/70 text-sm font-medium border border-foreground/20 hover:border-accent hover:text-foreground transition-all duration-300"
            >
              <span className="flex items-center justify-center gap-2">
                <Sparkles className="h-4 w-4 text-accent-purple group-hover:text-accent transition-colors" />
                Try Demo Without Account
              </span>
            </motion.button>

            {/* Terms */}
            {!isLoginMode && (
              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6 text-xs text-center text-foreground/40"
              >
                By creating an account, you agree to our{' '}
                <a href="#" className="text-accent hover:underline">Terms of Service</a>
                {' '}and{' '}
                <a href="#" className="text-accent hover:underline">Privacy Policy</a>
              </motion.p>
            )}
          </Card>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="p-6 text-center text-sm text-foreground/40">
        © 2025 Q&Ace. Master your interviews with AI.
      </footer>
    </div>
  )
}

// Wrap with Suspense for useSearchParams
export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    }>
      <AuthForm />
    </Suspense>
  )
}
