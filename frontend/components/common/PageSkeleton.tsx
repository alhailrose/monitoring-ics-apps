import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'

interface PageSkeletonProps {
  rows?: number
}

export function PageSkeleton({ rows = 5 }: PageSkeletonProps) {
  return (
    <div className="space-y-6 p-6">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-28" />
        </div>
        <Separator />
      </div>

      {/* Content rows skeleton */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    </div>
  )
}
