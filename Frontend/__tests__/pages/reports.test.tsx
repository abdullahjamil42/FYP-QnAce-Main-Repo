import { render, screen, waitFor } from '@testing-library/react'
import ReportsPage from '@/app/(app)/reports/page'

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

describe('ReportsPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders reports page correctly', () => {
    render(<ReportsPage />)
    const headings = screen.getAllByRole('heading', { name: /reports/i })
    expect(headings.length).toBeGreaterThan(0)
  })

  it('displays empty state when no reports', () => {
    render(<ReportsPage />)
    expect(screen.getByText(/no reports yet/i)).toBeInTheDocument()
    expect(screen.getByText(/complete a practice session/i)).toBeInTheDocument()
  })

  it('displays reports when available', async () => {
    const mockReports = [
      {
        id: 'report-1',
        sessionId: 'session-1',
        analysis: {
          overallScore: 85,
        },
        createdAt: new Date().toISOString(),
      },
      {
        id: 'report-2',
        sessionId: 'session-2',
        analysis: {
          overallScore: 72,
        },
        createdAt: new Date().toISOString(),
      },
    ]
    localStorage.setItem('qace_reports', JSON.stringify(mockReports))

    render(<ReportsPage />)
    
    await waitFor(() => {
      expect(screen.queryByText(/no reports yet/i)).not.toBeInTheDocument()
    })
    
    expect(screen.getAllByText(/practice session/i).length).toBeGreaterThan(0)
  })

  it('shows correct score badges', async () => {
    const mockReports = [
      {
        id: 'report-1',
        sessionId: 'session-1',
        analysis: {
          overallScore: 85,
        },
        createdAt: new Date().toISOString(),
      },
    ]
    localStorage.setItem('qace_reports', JSON.stringify(mockReports))

    render(<ReportsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument()
    })
  })
})

