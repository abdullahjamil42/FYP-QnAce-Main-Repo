import type { Meta, StoryObj } from '@storybook/react'
import { MediaRecorder } from '@/components/ui/media-recorder'

const meta: Meta<typeof MediaRecorder> = {
  title: 'Components/MediaRecorder',
  component: MediaRecorder,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof MediaRecorder>

export const Default: Story = {
  args: {
    audio: true,
    video: true,
  },
}

export const AudioOnly: Story = {
  args: {
    audio: true,
    video: false,
  },
}

export const VideoOnly: Story = {
  args: {
    audio: false,
    video: true,
  },
}

