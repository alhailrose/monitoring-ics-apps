"use client"

import { useEffect, useMemo, useState, type FormEvent } from "react"

import { GlassPanel } from "../../components/ui/GlassPanel"
import { OpsButton } from "../../components/ui/OpsButton"
import { OpsInput } from "../../components/ui/OpsInput"
import { OpsSelect } from "../../components/ui/OpsSelect"
import { StatusPill } from "../../components/ui/StatusPill"

const CUSTOMER_OPTIONS = [
  { label: "Aryanoble (aryanoble)", value: "aryanoble" },
  { label: "NABATI KSNI (nabati-ksni)", value: "nabati-ksni" },
  { label: "SADEWA (sadewa)", value: "sadewa" },
  { label: "FFI (ffi)", value: "ffi" },
]

const CHECK_OPTIONS = [
  { label: "★ All Checks (Cost, GuardDuty, CW, Notif)", value: "all-light" },
  { label: "★ All Checks + Backup & RDS", value: "all" },
  { label: "▶ Health Events", value: "health" },
  { label: "▶ Cost Anomalies", value: "cost" },
  { label: "▶ GuardDuty Findings", value: "guardduty" },
  { label: "▶ CloudWatch Alarms", value: "cloudwatch" },
  { label: "▶ Notifications", value: "notifications" },
  { label: "▶ Backup Status", value: "backup" },
  { label: "▶ Alarm Verification (>10m)", value: "alarm_verification" },
  { label: "▶ Daily Arbel (RDS)", value: "daily-arbel" },
  { label: "▶ Daily Budget", value: "daily-budget" },
  { label: "▶ EC2 List", value: "ec2list" },
]

type QueueRow = {
  id: string
  status: string
  customer: string
  check: string
}

type SubmitFeedback = {
  tone: "success" | "error"
  message: string
} | null

type HistoryItem = {
  job_id: string
  customer_id: string
  check_name: string
  status: string
}

const QUEUE_ROWS: QueueRow[] = [
  { id: "job-1028", status: "running", customer: "aryanoble", check: "daily-arbel" },
  { id: "job-1027", status: "queued", customer: "opal-ics", check: "nightly-audit" },
]

const POLL_INTERVAL_MS = 3000

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null
}

const readString = (value: unknown, fallback = ""): string => {
  return typeof value === "string" ? value : fallback
}

const parseProfiles = (value: string): string[] => {
  return value
    .split(",")
    .map((profile) => profile.trim())
    .filter((profile) => profile.length > 0)
}

const hasActiveJobForCustomer = (rows: QueueRow[], customerId: string): boolean => {
  return rows.some(
    (row) => row.customer === customerId && (row.status === "queued" || row.status === "running"),
  )
}

const isActiveStatus = (status: string): boolean => {
  return status === "queued" || status === "running"
}

const mergeCustomerRows = (
  existingRows: QueueRow[],
  historyRows: QueueRow[],
  customerId: string,
): QueueRow[] => {
  const customerLocalRows = existingRows.filter((row) => row.customer === customerId)
  const retainedRows = existingRows.filter((row) => row.customer !== customerId)
  const historyJobIds = new Set(historyRows.map((row) => row.id))

  const preservedActiveRows = customerLocalRows.filter((row) => {
    if (!isActiveStatus(row.status)) {
      return false
    }

    return !historyJobIds.has(row.id)
  })

  return [...historyRows, ...preservedActiveRows, ...retainedRows]
}

const normalizeHistoryItem = (value: unknown): HistoryItem | null => {
  if (!isRecord(value)) {
    return null
  }

  return {
    job_id: readString(value.job_id, "unknown-job"),
    customer_id: readString(value.customer_id, "unknown-customer"),
    check_name: readString(value.check_name, "unknown-check"),
    status: readString(value.status, "unknown"),
  }
}

function getNextLocalJobId(rows: QueueRow[]) {
  const largestId = rows.reduce((maxId, row) => {
    const parsed = Number.parseInt(row.id.replace(/^job-/, ""), 10)
    return Number.isNaN(parsed) ? maxId : Math.max(maxId, parsed)
  }, 0)

  return `job-${largestId + 1}`
}

export default function JobsPage() {
  const [queueRows, setQueueRows] = useState<QueueRow[]>(QUEUE_ROWS)
  const [submitFeedback, setSubmitFeedback] = useState<SubmitFeedback>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pollCustomerId, setPollCustomerId] = useState("")

  const shouldPoll = useMemo(() => {
    if (!pollCustomerId) {
      return false
    }

    return hasActiveJobForCustomer(queueRows, pollCustomerId)
  }, [pollCustomerId, queueRows])

  useEffect(() => {
    if (!shouldPoll) {
      return
    }

    let isMounted = true

    const loadHistory = async () => {
      try {
        const requestUrl = `/api/v1/history?customer_id=${encodeURIComponent(pollCustomerId)}`
        const response = await fetch(requestUrl)
        if (!response.ok) {
          return
        }

        const payload = (await response.json()) as { items?: unknown }
        if (!isMounted) {
          return
        }

        const historyRows = Array.isArray(payload.items)
          ? payload.items
              .map(normalizeHistoryItem)
              .filter((item): item is HistoryItem => item !== null)
              .map((item) => ({
                id: item.job_id,
                status: item.status,
                customer: item.customer_id,
                check: item.check_name,
              }))
          : []

        setQueueRows((existingRows) => mergeCustomerRows(existingRows, historyRows, pollCustomerId))
      } catch {
        // Keep the last rendered snapshot when refresh fails.
      }
    }

    void loadHistory()
    const intervalId = setInterval(() => {
      void loadHistory()
    }, POLL_INTERVAL_MS)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [pollCustomerId, shouldPoll])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const formElement = event.currentTarget
    const formData = new FormData(formElement)
    const customer = String(formData.get("customer_id") ?? "").trim()
    const check = String(formData.get("check_name") ?? "").trim()
    const profiles = parseProfiles(String(formData.get("profiles") ?? ""))

    if (!customer || !check) {
      setSubmitFeedback({
        tone: "error",
        message: "Customer and check are required to queue a run.",
      })
      return
    }

    setSubmitFeedback(null)
    setIsSubmitting(true)

    try {
      const response = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_id: customer,
          check_name: check,
          profiles,
        }),
      })

      if (!response.ok) {
        throw new Error("submit-failed")
      }

      const payload = (await response.json()) as { job_id?: unknown }
      const jobId = readString(payload.job_id, getNextLocalJobId(queueRows))

      setQueueRows((rows) => [{ id: jobId, status: "queued", customer, check }, ...rows])
      setPollCustomerId(customer)
      setSubmitFeedback({
        tone: "success",
        message: `Queued job ${jobId} for ${customer} / ${check}.`,
      })
      formElement.reset()
    } catch {
      setSubmitFeedback({
        tone: "error",
        message: "Failed to queue job. Please try again.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="jobs-page" aria-labelledby="jobs-page-title">
      <GlassPanel className="jobs-header">
        <p className="jobs-eyebrow">Manual Dispatch // QUEUE_MGR</p>
        <h1 id="jobs-page-title" className="jobs-title">
          Jobs
        </h1>
        <p className="jobs-description">
          Launch targeted customer checks and monitor queue health in one control surface.
        </p>
      </GlassPanel>

      <section className="jobs-grid" aria-label="Manual run controls and queue snapshot">
        <GlassPanel as="article" className="jobs-form-panel" aria-labelledby="jobs-form-heading">
          <h2 id="jobs-form-heading" className="jobs-panel-title">
            Manual run request
          </h2>
          <form className="jobs-form" onSubmit={handleSubmit}>
            <div className="jobs-field">
              <label htmlFor="job-customer">Customer</label>
              <OpsSelect
                id="job-customer"
                name="customer_id"
                required
                options={CUSTOMER_OPTIONS}
                defaultValue="aryanoble"
              />
            </div>

            <div className="jobs-field">
              <label htmlFor="job-check">Check</label>
              <OpsSelect
                id="job-check"
                name="check_name"
                required
                options={CHECK_OPTIONS}
                defaultValue="daily-arbel"
              />
            </div>

            <div className="jobs-field">
              <label htmlFor="job-profiles">Profiles</label>
              <OpsInput id="job-profiles" name="profiles" placeholder="sfa, hris" />
            </div>

            <OpsButton type="submit" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Run Now"}
            </OpsButton>
            {submitFeedback ? (
              <p
                className={`jobs-form-feedback jobs-form-feedback--${submitFeedback.tone}`}
                role={submitFeedback.tone === "error" ? "alert" : "status"}
                aria-live={submitFeedback.tone === "error" ? "assertive" : "polite"}
              >
                {submitFeedback.message}
              </p>
            ) : null}
          </form>
        </GlassPanel>

        <GlassPanel as="article" className="jobs-queue-panel" aria-labelledby="jobs-queue-heading">
          <h2 id="jobs-queue-heading" className="jobs-panel-title">
            Queue snapshot
          </h2>
          <div className="jobs-table-scroll" role="region" aria-label="Queue snapshot table">
            <table className="jobs-table">
              <caption className="jobs-table-caption">Latest dispatch statuses</caption>
              <thead>
                <tr>
                  <th scope="col">Job ID</th>
                  <th scope="col">Status</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Check</th>
                </tr>
              </thead>
              <tbody>
                {queueRows.length === 0 ? (
                  <tr>
                    <td colSpan={4}>No queued jobs yet.</td>
                  </tr>
                ) : (
                  queueRows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>
                        <StatusPill status={row.status} />
                      </td>
                      <td>{row.customer}</td>
                      <td>{row.check}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </GlassPanel>
      </section>
    </main>
  )
}
