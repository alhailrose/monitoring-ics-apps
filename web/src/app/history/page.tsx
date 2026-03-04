import { useEffect, useMemo, useState, type FormEvent } from "react"

import { toUserMessage } from "../../api/client"
import { listCustomers } from "../../api/customers"
import { getHistoryDetail, listHistory } from "../../api/history"
import { CopyableOutput } from "../../components/common/CopyableOutput"
import { LoadingState } from "../../components/common/LoadingState"
import { StatusBadge } from "../../components/common/StatusBadge"
import type { CheckMode, CheckStatus, Customer, HistoryDetail, HistorySummary } from "../../types/api"

type Filters = {
  customerId: string
  startDate: string
  endDate: string
  checkMode: CheckMode | ""
  checkName: string
}

const PAGE_SIZE = 20

const todayDate = () => new Date().toISOString().slice(0, 10)

const formatDateTime = (isoDate: string): string => {
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) {
    return isoDate
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

const formatDuration = (duration: number | null): string => {
  if (duration === null || Number.isNaN(duration)) {
    return "-"
  }
  return `${duration}s`
}

const aggregateStatus = (item: HistorySummary): CheckStatus => {
  if (item.results_summary.error > 0) return "ERROR"
  if (item.results_summary.warn > 0) return "WARN"
  return "OK"
}

export default function HistoryPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [items, setItems] = useState<HistorySummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)

  const [filters, setFilters] = useState<Filters>({
    customerId: "",
    startDate: "",
    endDate: "",
    checkMode: "",
    checkName: "",
  })

  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isMobileView, setIsMobileView] = useState(false)
  const [error, setError] = useState("")
  const [detail, setDetail] = useState<HistoryDetail | null>(null)

  useEffect(() => {
    if (!window.matchMedia) {
      return
    }

    const media = window.matchMedia("(max-width: 56rem)")
    const update = () => setIsMobileView(media.matches)
    update()

    media.addEventListener?.("change", update)
    return () => media.removeEventListener?.("change", update)
  }, [])

  useEffect(() => {
    let isMounted = true

    const init = async () => {
      setIsLoading(true)
      setError("")

      try {
        const rows = await listCustomers()
        if (!isMounted) {
          return
        }

        setCustomers(rows)

        const first = rows[0]
        if (!first) {
          setItems([])
          setTotal(0)
          return
        }

        const defaultFilters: Filters = {
          customerId: first.id,
          startDate: "",
          endDate: "",
          checkMode: "",
          checkName: "",
        }
        setFilters(defaultFilters)

        const history = await listHistory({
          customerId: first.id,
          limit: PAGE_SIZE,
          offset: 0,
        })

        if (!isMounted) {
          return
        }

        setItems(history.items)
        setTotal(history.total)
      } catch (loadError) {
        if (isMounted) {
          setError(toUserMessage(loadError, "Failed to load history."))
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void init()

    return () => {
      isMounted = false
    }
  }, [])

  const runSearch = async (targetOffset: number) => {
    if (!filters.customerId) {
      setError("Customer is required.")
      return
    }
    if (filters.startDate && filters.endDate && filters.startDate > filters.endDate) {
      setError("Start date cannot be later than end date.")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const data = await listHistory({
        customerId: filters.customerId,
        startDate: filters.startDate || undefined,
        endDate: filters.endDate || undefined,
        checkMode: filters.checkMode,
        checkName: filters.checkName,
        limit: PAGE_SIZE,
        offset: targetOffset,
      })

      setItems(data.items)
      setTotal(data.total)
      setOffset(targetOffset)
    } catch (searchError) {
      setError(toUserMessage(searchError, "Failed to fetch history."))
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await runSearch(0)
  }

  const onViewDetail = async (checkRunId: string) => {
    setIsLoadingDetail(true)
    setError("")

    try {
      const data = await getHistoryDetail(checkRunId)
      setDetail(data)
    } catch (detailError) {
      setError(toUserMessage(detailError, "Failed to load history detail."))
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const canPrevious = offset > 0
  const canNext = offset + PAGE_SIZE < total

  const pageLabel = useMemo(() => {
    if (total === 0) {
      return "No history"
    }

    const from = offset + 1
    const to = Math.min(offset + PAGE_SIZE, total)
    return `${from}-${to} of ${total}`
  }, [offset, total])

  return (
    <main className="ops-page history-page-v2" aria-labelledby="history-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="history-title">History</h1>
        <p>Filter check runs and inspect detailed output.</p>
      </section>

      <section className="ops-glass-panel checks-form-panel">
        <form className="checks-form" onSubmit={onSubmit}>
          <label htmlFor="history-customer">Customer</label>
          <select
            id="history-customer"
            className="ops-select"
            value={filters.customerId}
            onChange={(event) => setFilters((current) => ({ ...current, customerId: event.target.value }))}
            required
            disabled={isLoading}
          >
            <option value="" disabled>
              Select customer
            </option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.display_name} ({customer.name})
              </option>
            ))}
          </select>

          <label htmlFor="history-start-date">Start Date</label>
          <input
            id="history-start-date"
            className="ops-input"
            type="date"
            value={filters.startDate}
            onChange={(event) => setFilters((current) => ({ ...current, startDate: event.target.value }))}
            max={todayDate()}
            disabled={isLoading}
          />

          <label htmlFor="history-end-date">End Date</label>
          <input
            id="history-end-date"
            className="ops-input"
            type="date"
            value={filters.endDate}
            onChange={(event) => setFilters((current) => ({ ...current, endDate: event.target.value }))}
            max={todayDate()}
            disabled={isLoading}
          />

          <label htmlFor="history-mode">Check Mode</label>
          <select
            id="history-mode"
            className="ops-select"
            value={filters.checkMode}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                checkMode: event.target.value as CheckMode | "",
              }))
            }
            disabled={isLoading}
          >
            <option value="">Any</option>
            <option value="single">single</option>
            <option value="all">all</option>
            <option value="arbel">arbel</option>
          </select>

          <label htmlFor="history-check-name">Check Name</label>
          <input
            id="history-check-name"
            className="ops-input"
            value={filters.checkName}
            onChange={(event) => setFilters((current) => ({ ...current, checkName: event.target.value }))}
            placeholder="guardduty"
            disabled={isLoading}
          />

          <button className="ops-button" type="submit" disabled={isLoading}>
            {isLoading ? "Loading..." : "Apply Filters"}
          </button>
        </form>
      </section>

      {isLoading ? <LoadingState title="Loading history..." detail="Fetching check runs." /> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <section className="ops-glass-panel checks-result history-results" aria-label="History table">
        <header className="history-table-header">
          <h2>Runs</h2>
          <p>{pageLabel}</p>
        </header>

        {isMobileView ? (
          <ul className="history-run-cards">
            {items.length === 0 ? (
              <li className="history-run-card">No history found.</li>
            ) : (
              items.map((item) => (
                <li key={item.check_run_id} className="history-run-card">
                  <header className="history-run-head">
                    <h3>{item.check_name ?? item.check_mode}</h3>
                    <StatusBadge status={aggregateStatus(item)} />
                  </header>
                  <p className="history-run-meta">{formatDateTime(item.created_at)}</p>
                  <p className="history-run-meta">
                    Mode: {item.check_mode} | Duration: {formatDuration(item.execution_time_seconds)}
                  </p>
                  <p className="history-run-meta">
                    OK {item.results_summary.ok} | WARN {item.results_summary.warn} | ERROR {item.results_summary.error}
                  </p>
                  <p className="history-run-meta">Slack: {item.slack_sent ? "sent" : "not sent"}</p>
                  <button type="button" className="ops-button" onClick={() => onViewDetail(item.check_run_id)}>
                    Open Detail
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : (
          <div className="history-table-scroll">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Mode</th>
                  <th>Check</th>
                  <th>Duration</th>
                  <th>Summary</th>
                  <th>Slack</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={7}>No history found.</td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.check_run_id}>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>{item.check_mode}</td>
                      <td>{item.check_name ?? "-"}</td>
                      <td>{formatDuration(item.execution_time_seconds)}</td>
                      <td>
                        <StatusBadge status={aggregateStatus(item)} /> OK {item.results_summary.ok} | WARN {item.results_summary.warn} | ERROR {item.results_summary.error}
                      </td>
                      <td>{item.slack_sent ? "Yes" : "No"}</td>
                      <td>
                        <button type="button" className="ops-button" onClick={() => onViewDetail(item.check_run_id)}>
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="history-pagination">
          <button
            type="button"
            className="ops-button"
            onClick={() => runSearch(Math.max(0, offset - PAGE_SIZE))}
            disabled={!canPrevious || isLoading}
          >
            Previous
          </button>
          <button
            type="button"
            className="ops-button"
            onClick={() => runSearch(offset + PAGE_SIZE)}
            disabled={!canNext || isLoading}
          >
            Next
          </button>
        </div>
      </section>

      {isLoadingDetail ? <LoadingState title="Loading detail..." detail="Fetching check run detail." /> : null}

      {detail ? (
        <section className="ops-glass-panel checks-result" aria-label="History detail">
          <header className="history-detail-head">
            <h2>Run Detail: {detail.check_run_id}</h2>
            <button type="button" className="ops-button" onClick={() => setDetail(null)}>
              Close Detail
            </button>
          </header>
          <p>{detail.customer.display_name} | mode: {detail.check_mode} | Slack: {detail.slack_sent ? "sent" : "not sent"}</p>

          {detail.results.map((result, index) => (
            <article key={`${result.account.id}-${result.check_name}-${index}`} className="checks-result-row">
              <header>
                <h3>{result.account.display_name} ({result.account.profile_name})</h3>
                <StatusBadge status={result.status} />
              </header>
              <p>{result.summary}</p>
              <CopyableOutput title={`${result.check_name} output`} text={result.output || result.summary} />
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
