'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../../hooks/use-auth'
import { useForm } from 'react-hook-form'
import { User } from '../../../lib/mock-data'
import { setUser } from '../../../lib/auth'
import { useToast } from '@/components/ui/toast'
import { LogOut, AlertTriangle } from 'lucide-react'

export default function SettingsPage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const { addToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: user || {},
  })

  const onSubmit = (data: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...data }
      setUser(updatedUser)
      addToast({
        type: 'success',
        message: 'Profile updated successfully',
      })
    }
  }

  const handleLogout = () => {
    logout()
    addToast({
      type: 'success',
      message: 'You have been logged out',
    })
    router.push('/')
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-foreground/60">Manage your account and preferences</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <h2 className="text-xl font-semibold mb-4">Profile Information</h2>

          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-2">
              Full Name
            </label>
            <input
              id="name"
              type="text"
              {...register('name', { required: 'Name is required' })}
              className="w-full px-4 py-2 rounded-lg bg-white border border-foreground/20 text-gray-900 placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-invalid={errors.name ? 'true' : 'false'}
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-400">{errors.name.message as string}</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full px-4 py-2 rounded-lg bg-gray-200 border border-foreground/20 text-gray-500 cursor-not-allowed"
            />
            <p className="mt-1 text-xs text-foreground/60">Email cannot be changed</p>
          </div>

          <div>
            <label htmlFor="role" className="block text-sm font-medium mb-2">
              Role
            </label>
            <input
              id="role"
              type="text"
              {...register('role', { required: 'Role is required' })}
              className="w-full px-4 py-2 rounded-lg bg-white border border-foreground/20 text-gray-900 placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-invalid={errors.role ? 'true' : 'false'}
            />
            {errors.role && (
              <p className="mt-1 text-sm text-red-400">{errors.role.message as string}</p>
            )}
          </div>

          <div className="flex gap-4">
            <Button type="submit" variant="primary">
              Save Changes
            </Button>
          </div>
        </form>
      </Card>

      {/* Account Section */}
      <Card hoverable={false} className="border-red-500/20">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          Account
        </h2>
        
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
            <p className="text-sm text-foreground/70 mb-3">
              Logging out will end your current session. You can log back in anytime with your email and password.
            </p>
            <Button 
              variant="ghost" 
              onClick={handleLogout}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Log Out
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

