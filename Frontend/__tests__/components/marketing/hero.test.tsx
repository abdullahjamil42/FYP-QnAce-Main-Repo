import { render, screen } from '@testing-library/react'
import { Hero } from '@/components/marketing/hero'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

describe('Hero', () => {
  it('renders hero section correctly', () => {
    const { container } = render(<Hero />)
    // Hero section should be present - check for heading or container
    expect(container).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /master your interview/i })).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<Hero />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})

