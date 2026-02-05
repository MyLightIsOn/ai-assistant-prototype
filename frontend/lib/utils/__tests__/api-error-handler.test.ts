import { describe, it, expect, vi, beforeEach } from 'vitest'
import { handleApiError, getErrorMessage } from '../api-error-handler'
import { toast } from 'sonner'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

describe('api-error-handler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getErrorMessage', () => {
    it('returns correct message for 400 status', () => {
      expect(getErrorMessage(400)).toBe('Invalid request')
    })

    it('returns correct message for 401 status', () => {
      expect(getErrorMessage(401)).toBe('Authentication required')
    })

    it('returns correct message for 403 status', () => {
      expect(getErrorMessage(403)).toBe('Permission denied')
    })

    it('returns correct message for 404 status', () => {
      expect(getErrorMessage(404)).toBe('Resource not found')
    })

    it('returns correct message for 422 status', () => {
      expect(getErrorMessage(422)).toBe('Validation error')
    })

    it('returns correct message for 500 status', () => {
      expect(getErrorMessage(500)).toBe('Server error occurred')
    })

    it('returns generic message for unknown status', () => {
      expect(getErrorMessage(418)).toBe('An unexpected error occurred')
    })

    it('uses custom message when provided', () => {
      expect(getErrorMessage(404, 'Task not found')).toBe('Task not found')
    })
  })

  describe('handleApiError', () => {
    it('shows toast with error message', () => {
      handleApiError(404, 'Task not found')

      expect(toast.error).toHaveBeenCalledWith('Task not found')
    })

    it('uses default message for status code', () => {
      handleApiError(500)

      expect(toast.error).toHaveBeenCalledWith('Server error occurred')
    })

    it('returns error details object', () => {
      const result = handleApiError(422, 'Invalid task data')

      expect(result).toEqual({
        status: 422,
        message: 'Invalid task data',
      })
    })
  })
})
