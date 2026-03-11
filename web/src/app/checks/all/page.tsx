import { useEffect, useState } from "react"

import { executeChecks } from "../../../api/checks"
import { toUserMessage } from "../../../api/client"
import { listCustomers } from "../../../api/customers"
import { CopyableOutput } from "../../../components/common/CopyableOutput"
import { LoadingState } from "../../../components/common/LoadingState"
import { StatusBadge } from "../../../components/common/StatusBadge"
import type { Customer, ExecuteCheckResponse } from "../../../types/api"

export default function AllCheckPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>([])
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
          setSelectedCustomerIds([rows[0].id])
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

  const toggleCustomer = (id: string) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  const onRun = async () => {
    if (selectedCustomerIds.length === 0) {
      setError("Select at least one customer.")
      return
    }

    setIsExecuting(true)
    setError("")
    setResult(null)

    try {
      const data = await executeChecks({
        customer_ids: selectedCustomerIds,
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
        <p>Run template checks for selected customers across all active accounts.</p>
      </section>

      <section className="ops-glass-panel checks-form-panel">
        {isLoading ? (
          <LoadingState title="Loading customers..." />
        ) : (
          <div className="checks-form">
            <fieldset className="checks-fieldset" disabled={isExecuting}>
              <legend>Customers</legend>
              {customers.length === 0 ? (
                <p className="checks-help">No customers available. Add one in Customer Management.</p>
              ) : null}
              {customers.map((customer) => (
                <label key={customer.id} className="checks-inline-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCustomerIds.includes(customer.id)}
                    onChange={() => toggleCustomer(customer.id)}
                  />
                  {customer.display_name} ({customer.name})
                </label>
              ))}
            </fieldset>

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
              disabled={isExecuting || selectedCustomerIds.length === 0}
            >
              {isExecuting ? "Executing..." : "Run All Checks"}
            </button>
          </div>
        )}

        {isExecuting ? <LoadingState /> : null}
        {error ? <p className="form-error" role="alert">{error}</p> : null}
      </section>

      {result ? (
        <>
          <p className="checks-meta">Execution time: {result.execution_time_seconds}s</p>
          {result.check_runs.map((run) => {
            const custName = customers.find((c) => c.id === run.customer_id)?.display_name ?? run.customer_id
            const output = result.consolidated_outputs[run.customer_id] ?? ""
            const custResults = result.results.filter((r) => r.customer_id === run.customer_id)
            const grouped = Array.from(
              custResults.reduce((map, item) => {
                const bucket = map.get(item.check_name) ?? []
                bucket.push(item)
                map.set(item.check_name, bucket)
                return map
              }, new Map<string, typeof custResults>()),
            )

            return (
              <section key={run.customer_id} className="ops-glass-panel checks-result" aria-label={`${custName} output`}>
                <h2>{custName}</h2>
                <CopyableOutput title="Consolidated Output" text={output} />
                {grouped.map(([checkName, items]) => (
                  <article key={checkName} className="checks-result-row">
                    <h3>{checkName}</h3>
                    {items.map((item, index) => (
                      <div key={`${item.account.id}-${index}`} className="checks-result-line">
                        <span>{item.account.display_name} ({item.account.profile_name})</span>
                        <StatusBadge status={item.status} />
                      </div>
                    ))}
                  </article>
                ))}
              </section>
            )
          })}
        </>
      ) : null}
    </main>
  )
}
