'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Common filler words to highlight in transcriptions
 */
const FILLER_WORDS = [
    'um', 'uh', 'like', 'you know', 'so', 'basically', 'actually',
    'literally', 'honestly', 'i mean', 'kind of', 'sort of',
    'i guess', 'right', 'well'
]

export interface TextHighlighterProps {
    text: string
    editable?: boolean
    onChange?: (text: string) => void
    className?: string
    highlightFillers?: boolean
    highlightPauses?: boolean
}

interface HighlightedSegment {
    text: string
    type: 'normal' | 'filler' | 'pause'
}

/**
 * Text Highlighter Component
 * 
 * Displays transcribed text with visual highlighting for:
 * - Filler words (um, uh, like, you know, etc.)
 * - Long pauses ([pause] markers)
 * 
 * Optional: Editable mode for user corrections before submission.
 */
export function TextHighlighter({
    text,
    editable = false,
    onChange,
    className,
    highlightFillers = true,
    highlightPauses = true,
}: TextHighlighterProps) {
    const [editedText, setEditedText] = React.useState(text)
    const [isEditing, setIsEditing] = React.useState(false)

    React.useEffect(() => {
        setEditedText(text)
    }, [text])

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setEditedText(e.target.value)
        onChange?.(e.target.value)
    }

    /**
     * Parse text and identify filler words and pauses for highlighting
     */
    const parseTextForHighlights = (inputText: string): HighlightedSegment[] => {
        if (!inputText) return []

        const segments: HighlightedSegment[] = []
        let remaining = inputText

        // Create regex for filler words (case insensitive)
        const fillerPattern = new RegExp(
            `\\b(${FILLER_WORDS.join('|')})\\b`,
            'gi'
        )

        // Create regex for pause markers
        const pausePattern = /\[pause\]|\[long pause\]|\.\.\./gi

        let lastIndex = 0
        const allMatches: Array<{ match: string; index: number; type: 'filler' | 'pause' }> = []

        // Find all filler words
        if (highlightFillers) {
            let match
            while ((match = fillerPattern.exec(inputText)) !== null) {
                allMatches.push({
                    match: match[0],
                    index: match.index,
                    type: 'filler',
                })
            }
        }

        // Find all pause markers
        if (highlightPauses) {
            let match
            while ((match = pausePattern.exec(inputText)) !== null) {
                allMatches.push({
                    match: match[0],
                    index: match.index,
                    type: 'pause',
                })
            }
        }

        // Sort by index
        allMatches.sort((a, b) => a.index - b.index)

        // Build segments
        for (const match of allMatches) {
            // Add normal text before this match
            if (match.index > lastIndex) {
                segments.push({
                    text: inputText.slice(lastIndex, match.index),
                    type: 'normal',
                })
            }

            // Add the highlighted match
            segments.push({
                text: match.match,
                type: match.type,
            })

            lastIndex = match.index + match.match.length
        }

        // Add remaining text
        if (lastIndex < inputText.length) {
            segments.push({
                text: inputText.slice(lastIndex),
                type: 'normal',
            })
        }

        return segments
    }

    const segments = parseTextForHighlights(editedText)
    const fillerCount = segments.filter((s) => s.type === 'filler').length

    // Editing mode - show textarea
    if (editable && isEditing) {
        return (
            <div className={cn('space-y-2', className)}>
                <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground/60">Editing transcription</span>
                    <button
                        onClick={() => setIsEditing(false)}
                        className="text-sm text-accent hover:underline"
                    >
                        Done
                    </button>
                </div>
                <textarea
                    value={editedText}
                    onChange={handleChange}
                    className="w-full min-h-[150px] p-3 rounded-lg bg-background border border-border focus:border-accent focus:ring-1 focus:ring-accent resize-none"
                />
            </div>
        )
    }

    // Display mode - show highlighted text
    return (
        <div className={cn('space-y-2', className)}>
            {editable && (
                <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground/60">
                        {fillerCount > 0 && (
                            <span className="text-yellow-400">
                                {fillerCount} filler word{fillerCount > 1 ? 's' : ''} detected
                            </span>
                        )}
                    </span>
                    <button
                        onClick={() => setIsEditing(true)}
                        className="text-sm text-accent hover:underline"
                    >
                        Edit
                    </button>
                </div>
            )}
            <div className="p-3 rounded-lg bg-background/50 border border-border/50 leading-relaxed">
                {segments.map((segment, i) => (
                    <span
                        key={i}
                        className={cn(
                            segment.type === 'filler' &&
                            'bg-yellow-500/30 text-yellow-300 px-1 rounded',
                            segment.type === 'pause' &&
                            'bg-orange-500/30 text-orange-300 px-1 rounded italic'
                        )}
                    >
                        {segment.text}
                    </span>
                ))}
                {!editedText && (
                    <span className="text-foreground/40 italic">No transcription yet...</span>
                )}
            </div>
        </div>
    )
}

/**
 * Get filler word statistics for the given text
 */
export function getFillerStats(text: string): {
    count: number
    words: string[]
    percentage: number
} {
    const words = text.toLowerCase().split(/\s+/)
    const fillers: string[] = []

    for (const word of words) {
        if (FILLER_WORDS.includes(word)) {
            fillers.push(word)
        }
    }

    return {
        count: fillers.length,
        words: fillers,
        percentage: words.length > 0 ? (fillers.length / words.length) * 100 : 0,
    }
}
