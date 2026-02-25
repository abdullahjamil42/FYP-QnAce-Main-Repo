'use client'

import * as React from 'react'
import Link from 'next/link'
import { motion, Variants } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Menu, X } from 'lucide-react'
import { useReducedMotion } from '@/hooks/use-reduced-motion'
import { cn } from '@/lib/utils'
import { Logo } from './logo'
import { useAuth } from '@/hooks/use-auth'
import { useRouter } from 'next/navigation'

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)
  const [scrolled, setScrolled] = React.useState(false)
  const prefersReducedMotion = useReducedMotion()
  const { isAuthenticated, needsOnboarding } = useAuth()
  const router = useRouter()

  React.useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Navigation links
  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '#features', label: 'Features' },
    { href: '#demo', label: 'Demo' },
  ]

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith('#')) {
      e.preventDefault()
      const element = document.querySelector(href)
      if (element) {
        const offset = 80
        const elementPosition = element.getBoundingClientRect().top
        const offsetPosition = elementPosition + window.pageYOffset - offset

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth',
        })
      }
      setMobileMenuOpen(false)
    } else if (href === '/') {
      e.preventDefault()
      window.scrollTo({ top: 0, behavior: 'smooth' })
      setMobileMenuOpen(false)
    } else {
      setMobileMenuOpen(false)
    }
  }

  const handleGetStarted = () => {
    setMobileMenuOpen(false)
    if (isAuthenticated) {
      if (needsOnboarding) {
        router.push('/onboarding')
      } else {
        router.push('/dashboard')
      }
    } else {
      router.push('/login')
    }
  }

  const variants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
        initial: { opacity: 0, y: -20 },
        animate: { opacity: 1, y: 0 },
      }

  return (
    <motion.nav
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-background/80 backdrop-blur-md border-b border-foreground/10 shadow-lg'
          : 'bg-transparent'
      )}
      variants={variants}
      initial="initial"
      animate="animate"
      transition={{ duration: 0.3 }}
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <Logo size="md" />

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={(e) => handleNavClick(e, link.href)}
                className="text-sm font-medium text-foreground/70 hover:text-foreground transition-colors relative group"
              >
                {link.label}
                <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-accent transition-all group-hover:w-full" />
              </Link>
            ))}

            <Button 
              variant="primary" 
              size="sm"
              onClick={handleGetStarted}
            >
              Get Started
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 rounded-lg text-foreground/70 hover:text-foreground hover:bg-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        <motion.div
          className={cn(
            'md:hidden overflow-hidden',
            mobileMenuOpen ? 'max-h-96' : 'max-h-0'
          )}
          initial={false}
          animate={{
            height: mobileMenuOpen ? 'auto' : 0,
          }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
        >
          <div className="py-4 space-y-3 border-t border-foreground/10">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={(e) => handleNavClick(e, link.href)}
                className="block px-4 py-2 text-sm font-medium text-foreground/70 hover:text-foreground hover:bg-foreground/10 rounded-lg transition-colors"
              >
                {link.label}
              </Link>
            ))}

            <div className="px-4 pt-2">
              <Button 
                variant="primary" 
                className="w-full"
                onClick={handleGetStarted}
              >
                Get Started
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.nav>
  )
}
