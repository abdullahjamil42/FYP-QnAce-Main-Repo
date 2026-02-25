'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Edit, Trash2 } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { useForm } from 'react-hook-form'
import { useToast } from '@/components/ui/toast'

interface Question {
  id: string
  text: string
  category: string
  difficulty: string
  tags: string[]
  createdAt: string
}

// Default questions
const defaultQuestions: Question[] = [
  {
    id: 'q-1',
    text: 'Tell me about yourself and your background.',
    category: 'behavioral',
    difficulty: 'easy',
    tags: ['introduction', 'background'],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'q-2',
    text: 'Describe a challenging project you worked on and how you handled it.',
    category: 'behavioral',
    difficulty: 'medium',
    tags: ['problem-solving', 'experience'],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'q-3',
    text: 'What are your greatest strengths and weaknesses?',
    category: 'behavioral',
    difficulty: 'easy',
    tags: ['self-awareness', 'growth'],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'q-4',
    text: 'Where do you see yourself in 5 years?',
    category: 'behavioral',
    difficulty: 'medium',
    tags: ['goals', 'career'],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'q-5',
    text: 'Explain a time when you had to work under pressure.',
    category: 'behavioral',
    difficulty: 'medium',
    tags: ['pressure', 'time-management'],
    createdAt: new Date().toISOString(),
  },
]

// Get questions from localStorage or use defaults
function getQuestions(): Question[] {
  if (typeof window === 'undefined') return defaultQuestions
  const stored = localStorage.getItem('qace_questions')
  if (stored) {
    return JSON.parse(stored)
  }
  localStorage.setItem('qace_questions', JSON.stringify(defaultQuestions))
  return defaultQuestions
}

// Save questions to localStorage
function saveQuestions(questions: Question[]) {
  if (typeof window === 'undefined') return
  localStorage.setItem('qace_questions', JSON.stringify(questions))
}

export default function AdminPage() {
  const [questions, setQuestions] = React.useState<Question[]>([])
  const [isModalOpen, setIsModalOpen] = React.useState(false)
  const [editingQuestion, setEditingQuestion] = React.useState<Question | null>(null)
  const { addToast } = useToast()

  // Load questions on mount
  React.useEffect(() => {
    setQuestions(getQuestions())
  }, [])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    defaultValues: {
      text: '',
      category: '',
      difficulty: 'medium',
      tags: '',
    },
  })

  React.useEffect(() => {
    if (editingQuestion) {
      reset({
        text: editingQuestion.text,
        category: editingQuestion.category,
        difficulty: editingQuestion.difficulty,
        tags: editingQuestion.tags.join(', '),
      })
    }
  }, [editingQuestion, reset])

  const onSubmit = (data: any) => {
    const tags = data.tags.split(',').map((tag: string) => tag.trim()).filter(Boolean)
    
    let updatedQuestions: Question[]
    
    if (editingQuestion) {
      // Update existing question
      updatedQuestions = questions.map((q) =>
        q.id === editingQuestion.id
          ? { ...q, ...data, tags }
          : q
      )
      setQuestions(updatedQuestions)
      addToast({ type: 'success', message: 'Question updated successfully' })
    } else {
      // Add new question
      const newQuestion: Question = {
        id: `q-${Date.now()}`,
        ...data,
        tags,
        createdAt: new Date().toISOString(),
      }
      updatedQuestions = [...questions, newQuestion]
      setQuestions(updatedQuestions)
      addToast({ type: 'success', message: 'Question added successfully' })
    }
    
    // Save to localStorage
    saveQuestions(updatedQuestions)
    
    setIsModalOpen(false)
    setEditingQuestion(null)
    reset()
  }

  const handleEdit = (question: Question) => {
    setEditingQuestion(question)
    setIsModalOpen(true)
  }

  const handleDelete = (id: string) => {
    const updatedQuestions = questions.filter((q) => q.id !== id)
    setQuestions(updatedQuestions)
    saveQuestions(updatedQuestions)
    addToast({ type: 'success', message: 'Question deleted successfully' })
  }

  const handleNew = () => {
    setEditingQuestion(null)
    reset()
    setIsModalOpen(true)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Question Bank Management</h1>
          <p className="text-foreground/60">Manage interview questions for practice sessions</p>
        </div>
        <Button onClick={handleNew} variant="primary">
          <Plus className="mr-2 h-5 w-5" />
          Add Question
        </Button>
      </div>

      <div className="space-y-4">
        {questions.map((question) => (
          <Card key={question.id} hoverable>
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-3">
                <div>
                  <h3 className="font-semibold mb-2">{question.text}</h3>
                  <div className="flex items-center gap-2">
                    <Badge variant="info">{question.category}</Badge>
                    <Badge variant="default">{question.difficulty}</Badge>
                    {question.tags.map((tag) => (
                      <Badge key={tag} variant="default" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleEdit(question)}
                  aria-label={`Edit question ${question.id}`}
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(question.id)}
                  aria-label={`Delete question ${question.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setEditingQuestion(null)
          reset()
        }}
        title={editingQuestion ? 'Edit Question' : 'Add New Question'}
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="text" className="block text-sm font-medium mb-2">
              Question Text
            </label>
            <textarea
              id="text"
              {...register('text', { required: 'Question text is required' })}
              className="w-full px-4 py-2 rounded-lg bg-white border border-gray-300 text-black placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent min-h-[100px]"
              aria-invalid={errors.text ? 'true' : 'false'}
            />
            {errors.text && (
              <p className="mt-1 text-sm text-red-400">{errors.text.message as string}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="category" className="block text-sm font-medium mb-2">
                Category
              </label>
              <input
                id="category"
                type="text"
                {...register('category', { required: 'Category is required' })}
                className="w-full px-4 py-2 rounded-lg bg-white border border-gray-300 text-black placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-invalid={errors.category ? 'true' : 'false'}
              />
              {errors.category && (
                <p className="mt-1 text-sm text-red-400">{errors.category.message as string}</p>
              )}
            </div>

            <div>
              <label htmlFor="difficulty" className="block text-sm font-medium mb-2">
                Difficulty
              </label>
              <select
                id="difficulty"
                {...register('difficulty', { required: 'Difficulty is required' })}
                className="w-full px-4 py-2 rounded-lg bg-white border border-gray-300 text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-invalid={errors.difficulty ? 'true' : 'false'}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              {errors.difficulty && (
                <p className="mt-1 text-sm text-red-400">{errors.difficulty.message as string}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="tags" className="block text-sm font-medium mb-2">
              Tags (comma-separated)
            </label>
            <input
              id="tags"
              type="text"
              {...register('tags')}
              className="w-full px-4 py-2 rounded-lg bg-white border border-gray-300 text-black placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              placeholder="e.g., system-design, scalability"
            />
          </div>

          <div className="flex gap-4 justify-end">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setIsModalOpen(false)
                setEditingQuestion(null)
                reset()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              {editingQuestion ? 'Update' : 'Add'} Question
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

