'use client'
import { PageError } from '@/components/common/PageError'
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <PageError error={error} reset={reset} title="Failed to load dashboard" />
}
