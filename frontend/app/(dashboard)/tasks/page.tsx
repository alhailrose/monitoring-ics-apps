import { PageHeader } from '@/components/common/PageHeader'
import { TaskScheduleTable } from '@/components/tasks/TaskScheduleTable'
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import type { ReportSchedule } from '@/lib/schedule-utils'
import { Badge } from '@/components/ui/badge'

// TODO: Replace with real API call to GET /api/v1/tasks/schedules once backend is ready
function getMockSchedules(customers: { id: string; display_name: string }[]): ReportSchedule[] {
  return customers.map((c) => ({
    customerId: c.id,
    customerName: c.display_name,
    scheduleTimes: ['08:00', '19:00'],
    lastReportSentAt: null,
    lastCheckRunAt: null,
    reportSentWithLastRun: false,
  }))
}

export default async function TasksPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const customers = Array.isArray(customersRaw) ? customersRaw : []
  const schedules = getMockSchedules(customers)

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Tasks"
        description="Manage report schedules per customer"
        actions={<Badge variant="outline" className="text-xs text-amber-400 border-amber-400/40">Coming Soon</Badge>}
      />
      <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-sm text-amber-400/80">
        Schedule configuration is not yet connected to the backend. The data shown below is a preview of the planned interface.
      </div>
      <TaskScheduleTable schedules={schedules} />
    </div>
  )
}
