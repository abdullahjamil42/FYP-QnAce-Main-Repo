import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ToastProvider } from '@/components/ui/toast'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Q&Ace - AI-Powered Interview Preparation',
  description: 'Prepare for high-stakes interviews with AI-powered multi-modal feedback',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  )
}

