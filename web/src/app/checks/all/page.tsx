import { useEffect, useMemo, useState } from "react"

import { executeChecks } from "../../../api/checks"
import { toUserMessage } from "../../../api/client"
import { listCustomers } from "../../../api/customers"
import { CopyableOutput } from "../../../components/common/CopyableOutput"
import { LoadingState } from "../../../components/common/LoadingState"
import { StatusBadge } from "../../../components/common/StatusBadge"
import type { Customer, ExecuteCheckResponse } from "../../../types/api"

const groupByCheck = (result: ExecuteCheckResponse | null) => {
  if (!result) {
    return [] as Array<{ checkName: string; items: ExecuteCheckResponse["results"] }>
  }

  const grouped = new Map<string, ExecuteCheckResponse["results"]>()
  for (const item of result.results) {
    const bucket = grouped.get(item.check_name) ?? []
    bucket.push(item)
    grouped.set(item.check_name, bucket)
  }

  return Array.from(grouped.entries()).map(([checkName, items]) => ({ checkName, items }))
}

export default function AllCheckPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomerId, setSelectedCustomerId] = useState("")
  const [sendSlack, setSendSlack] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<ExecuteCheckResponse | null>(null)

  useEffect(() => {
    let isMounted = true

    const load = async () => {
      setIsLoading(true)
      setError("")

      try {
        const rows = await listCustomers()
        if (!isMounted) {
          return
        }

        setCustomers(rows)
        if (rows[0]) {
          setSelectedCustomerId(rows[0].id)
        }
      } catch (loadError) {
        if (isMounted) {
          setError(toUserMessage(loadError, "Failed to load customers."))
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void load()

    return () => {
      isMounted = false
    }
  }, [])

  const selectedCustomer = useMemo(
    () => customers.find((customer) => customer.id === selectedCustomerId) ?? null,
    [customers, selectedCustomerId],
  )

  const groupedResults = useMemo(() => groupByCheck(result), [result])
  const activeAccountCount = selectedCustomer?.accounts.filter((account) => account.is_active).length ?? 0

  const onRun = async () => {
    if (!selectedCustomerId) {
      setError("Customer is required.")
      return
    }

    setIsExecuting(true)
    setError("")
    setResult(null)

    try {
      const data = await executeChecks({
        customer_id: selectedCustomerId,
        mode: "all",
        send_slack: sendSlack,
      })
      setResult(data)
    } catch (runError) {
      setError(toUserMessage(runError, "Failed to execute all checks."))
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <main className="ops-page checks-page" aria-labelledby="all-check-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="all-check-title">All Check</h1>
        <p>Run template checks for selected customer across all active accounts.</p>
      </section>

      <section className="ops-glass-panel checks-form-panel">
        {isLoading ? (
          <LoadingState title="Loading customers..." />
        ) : (
          <div className="checks-form">
            <label htmlFor="all-customer">Customer</label>
            <select
              id="all-customer"
              className="ops-select"
              value={selectedCustomerId}
              onChange={(event) => setSelectedCustomerId(event.target.value)}
              disabled={isExecuting || customers.length === 0}
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

            <p>Active accounts: {activeAccountCount}</p>
            {customers.length === 0 ? <p className="checks-help">No customers available. Add one in Customer Management.</p> : null}
            {selectedCustomerId && activeAccountCount === 0 ? (
              <p className="checks-help">Selected customer has no active accounts.</p>
            ) : null}

            <label className="checks-inline-checkbox">
              <input
                type="checkbox"
                checked={sendSlack}
                onChange={(event) => setSendSlack(event.target.checked)}
                disabled={isExecuting}
              />
              Send to Slack
            </label>

            <button
              className="ops-button"
              type="button"
              onClick={onRun}
              disabled={isExecuting || !selectedCustomerId || activeAccountCount === 0}
            >
              {isExecuting ? "Executing..." : "Run All Checks"}
            </button>
          </div>
        )}

        {isExecuting ? <LoadingState /> : null}
        {error ? <p className="form-error" role="alert">{error}</p> : null}
      </section>

      {result ? (
        <section className="ops-glass-panel checks-result" aria-label="All check output">
          <p className="checks-meta">Execution time: {result.execution_time_seconds}s</p>
          <CopyableOutput title="Consolidated Output" text={result.consolidated_output} />

          {groupedResults.map((group) => (
            <article key={group.checkName} className="checks-result-row">
              <h2>{group.checkName}</h2>
              {group.items.map((item, index) => (
                <div key={`${item.account.id}-${index}`} className="checks-result-line">
                  <span>{item.account.display_name} ({item.account.profile_name})</span>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
