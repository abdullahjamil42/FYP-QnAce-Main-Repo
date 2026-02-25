import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { Card } from '@/components/ui/card'

expect.extend(toHaveNoViolations)

describe('Card', () => {
  it('renders children correctly', () => {
    render(
      <Card>
        <p>Card content</p>
      </Card>
    )
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = render(
      <Card>
        <p>Card content</p>
      </Card>
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('supports hoverable prop', () => {
    const { rerender } = render(<Card hoverable>Hoverable</Card>)
    expect(screen.getByRole('button')).toBeInTheDocument()

    rerender(<Card hoverable={false}>Not hoverable</Card>)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

