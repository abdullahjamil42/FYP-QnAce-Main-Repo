'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

// Redirect to login page which now has both login and signup with toggle
export default function SignupPage() {
  const router = useRouter()
  
  useEffect(() => {
    // Redirect to login page and set signup mode via URL param
    router.replace('/login?mode=signup')
  }, [router])
  
  return null
}
