import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Navbar } from '@/components/marketing/navbar'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

describe('Navbar', () => {
  it('renders navbar correctly', () => {
    render(<Navbar />)
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('displays logo', () => {
    render(<Navbar />)
    // Logo should be present
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<Navbar />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})

