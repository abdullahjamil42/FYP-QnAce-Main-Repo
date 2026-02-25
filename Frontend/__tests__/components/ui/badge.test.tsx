import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/badge'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

describe('Badge', () => {
  it('renders badge correctly', () => {
    render(<Badge>Test Badge</Badge>)
    expect(screen.getByText('Test Badge')).toBeInTheDocument()
  })

  it('supports different variants', () => {
    const { rerender } = render(<Badge variant="success">Success</Badge>)
    expect(screen.getByText('Success')).toBeInTheDocument()

    rerender(<Badge variant="error">Error</Badge>)
    expect(screen.getByText('Error')).toBeInTheDocument()

    rerender(<Badge variant="info">Info</Badge>)
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<Badge>Accessible Badge</Badge>)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})

