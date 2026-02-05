import { toast } from 'sonner'

export interface ApiError {
  status: number
  message: string
}

const ERROR_MESSAGES: Record<number, string> = {
  400: 'Invalid request',
  401: 'Authentication required',
  403: 'Permission denied',
  404: 'Resource not found',
  422: 'Validation error',
  500: 'Server error occurred',
  502: 'Bad gateway',
  503: 'Service unavailable',
}

/**
 * Get user-friendly error message for HTTP status code
 */
export function getErrorMessage(status: number, customMessage?: string): string {
  if (customMessage) {
    return customMessage
  }
  return ERROR_MESSAGES[status] || 'An unexpected error occurred'
}

/**
 * Handle API errors with toast notification
 */
export function handleApiError(status: number, customMessage?: string): ApiError {
  const message = getErrorMessage(status, customMessage)
  toast.error(message)

  return {
    status,
    message,
  }
}

/**
 * Handle fetch response errors
 */
export async function handleFetchError(response: Response, customMessage?: string): Promise<ApiError> {
  let errorDetails = customMessage

  // Try to extract error details from response body
  try {
    const data = await response.json()
    if (data.error || data.message) {
      errorDetails = data.error || data.message
    }
  } catch {
    // Ignore JSON parse errors
  }

  return handleApiError(response.status, errorDetails)
}
