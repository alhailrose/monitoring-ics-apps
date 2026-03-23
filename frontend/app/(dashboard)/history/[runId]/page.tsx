// Server Component — fetches run detail server-side
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getToken } from '@/lib/server-token'
import { getRunDetail } from '@/lib/api/history'
import { PageHeader } from '@/components/common/PageHeader'
import { RunDetail } from '@/components/history/RunDetail'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const { runId } = await params
  const token = await getToken()

  let run
  try {
    run = await getRunDetail(runId, token)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound()
    throw err
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/history">← Back</Link>
        </Button>
      </div>
      <PageHeader
        title={run.customer?.display_name ?? run.check_name ?? 'Check Run'}
        description={`${run.check_name ?? run.check_mode} · ${run.check_run_id}`}
      />
      <RunDetail run={run} />
    </div>
  )
}
