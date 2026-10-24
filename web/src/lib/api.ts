import createClient from 'openapi-fetch'
import type { components, paths } from './api-schema'

export type Schemas = components['schemas']

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = createClient<paths>({
  baseUrl: API_URL,
  // Look fetch up on each call (not once at start-up), so tests can stub it.
  fetch: (request) => globalThis.fetch(request),
})

/** An API error with a message a person can read. */
export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

interface ValidationIssue {
  msg: string
  loc?: (string | number)[]
}

function messageFrom(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return (detail as ValidationIssue[])
        .map((issue) => issue.msg.replace(/^Value error, /, ''))
        .join(' ')
    }
  }
  return 'The server could not answer. Try again in a moment.'
}

/** Turn an openapi-fetch result into data, or throw an ApiError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    throw new ApiError(messageFrom(result.error), result.response.status)
  }
  return result.data
}
