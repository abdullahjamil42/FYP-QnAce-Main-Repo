import type { Meta, StoryObj } from '@storybook/react'
import { Card } from '@/components/ui/card'

const meta: Meta<typeof Card> = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    hoverable: {
      control: 'boolean',
    },
  },
}

export default meta
type Story = StoryObj<typeof Card>

export const Default: Story = {
  args: {
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Card Title</h3>
        <p className="text-foreground/60">This is a basic card component with some content.</p>
      </div>
    ),
  },
}

export const Hoverable: Story = {
  args: {
    hoverable: true,
    children: (
      <div>
        <h3 className="text-lg font-semibold mb-2">Hoverable Card</h3>
        <p className="text-foreground/60">This card has hover effects enabled.</p>
      </div>
    ),
  },
}

export const WithContent: Story = {
  args: {
    children: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Card with Multiple Elements</h3>
        <p className="text-foreground/60">This card contains multiple elements and demonstrates spacing.</p>
        <button className="px-4 py-2 bg-accent text-background rounded-lg">Action Button</button>
      </div>
    ),
  },
}

