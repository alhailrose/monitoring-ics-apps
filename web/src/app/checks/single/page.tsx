import { useEffect, useMemo, useState, type FormEvent } from "react"

import { executeChecks, listAvailableChecks } from "../../../api/checks"
import { toUserMessage } from "../../../api/client"
import { listCustomers } from "../../../api/customers"
import { CopyableOutput } from "../../../components/common/CopyableOutput"
import { LoadingState } from "../../../components/common/LoadingState"
import { StatusBadge } from "../../../components/common/StatusBadge"
import type { AvailableCheck, Customer, ExecuteCheckResponse } from "../../../types/api"

export default function SingleCheckPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [checks, setChecks] = useState<AvailableCheck[]>([])
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>([])
  const [selectedCheckName, setSelectedCheckName] = useState("")
  const [selectAllAccounts, setSelectAllAccounts] = useState(false)
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([])
  const [sendSlack, setSendSlack] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<ExecuteCheckResponse | null>(null)

  useEffect(() => {
    let isMounted = true

    const loadData = async () => {
      setIsLoading(true)
      setError("")

      try {
        const [customerRows, checkRows] = await Promise.all([listCustomers(), listAvailableChecks()])

        if (!isMounted) {
          return
        }

        setCustomers(customerRows)
        setChecks(checkRows)

        const firstCustomer = customerRows[0]
        setSelectedCustomerIds(firstCustomer ? [firstCustomer.id] : [])

        const firstCheck = checkRows[0]
        if (firstCheck) {
          setSelectedCheckName(firstCheck.name)
        }
      } catch (loadError) {
        if (isMounted) {
          setError(toUserMessage(loadError, "Failed to load form data."))
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void loadData()

    return () => {
      isMounted = false
    }
  }, [])

  const selectedCustomers = useMemo(
    () => customers.filter((c) => selectedCustomerIds.includes(c.id)),
    [customers, selectedCustomerIds],
  )
  const accounts = useMemo(
    () => selectedCustomers.flatMap((c) => c.accounts.filter((a) => a.is_active)),
    [selectedCustomers],
  )

  useEffect(() => {
    setSelectedAccountIds([])
    setSelectAllAccounts(false)
  }, [selectedCustomerIds])

  const toggleCustomer = (id: string) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  const onToggleSelectAll = (checked: boolean) => {
    setSelectAllAccounts(checked)
    if (checked) {
      setSelectedAccountIds(accounts.map((account) => account.id))
    } else {
      setSelectedAccountIds([])
    }
  }

  const toggleAccount = (accountId: string) => {
    setSelectedAccountIds((current) => {
      if (current.includes(accountId)) {
        return current.filter((id) => id !== accountId)
      }
      return [...current, accountId]
    })
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedCustomerIds.length || !selectedCheckName) {
      setError("Customer and check type are required.")
      return
    }
    if (!selectAllAccounts && selectedAccountIds.length === 0) {
      setError("Select at least one account or enable Select All Accounts.")
      return
    }

    setIsExecuting(true)
    setError("")
    setResult(null)

    try {
      const executeResult = await executeChecks({
        customer_ids: selectedCustomerIds,
        mode: "single",
        check_name: selectedCheckName,
        account_ids: selectAllAccounts ? null : selectedAccountIds,
        send_slack: sendSlack,
      })
      setResult(executeResult)
    } catch (executeError) {
      setError(toUserMessage(executeError, "Failed to execute check."))
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <main className="ops-page checks-page" aria-labelledby="single-check-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="single-check-title">Single Check</h1>
        <p>Run one monitoring check and get immediate output.</p>
      </section>

      <section className="ops-glass-panel checks-form-panel">
        {isLoading ? (
          <LoadingState title="Loading data..." detail="Fetching customers and check types." />
        ) : (
          <form className="checks-form" onSubmit={onSubmit}>
            <fieldset className="checks-fieldset" disabled={isExecuting}>
              <legend>Customers</legend>
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

            <label htmlFor="single-check">Check Type</label>
            <select
              id="single-check"
              className="ops-select"
              value={selectedCheckName}
              onChange={(event) => setSelectedCheckName(event.target.value)}
              required
              disabled={isExecuting}
            >
              <option value="" disabled>
                Select check type
              </option>
              {checks.map((check) => (
                <option key={check.name} value={check.name}>
                  {check.name}
                </option>
              ))}
            </select>

            <fieldset className="checks-fieldset" disabled={isExecuting}>
              <legend>Accounts</legend>
              <label className="checks-inline-checkbox">
                <input
                  type="checkbox"
                  checked={selectAllAccounts}
                  onChange={(event) => onToggleSelectAll(event.target.checked)}
                />
                Select All Accounts
              </label>

              <div className="checks-account-list">
                {accounts.length === 0 ? <p className="checks-help">No active accounts available.</p> : null}
                {accounts.map((account) => (
                  <label key={account.id} className="checks-inline-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedAccountIds.includes(account.id)}
                      onChange={() => toggleAccount(account.id)}
                      disabled={selectAllAccounts}
                    />
                    {account.display_name} ({account.profile_name})
                  </label>
                ))}
              </div>
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
              type="submit"
              disabled={isExecuting || accounts.length === 0 || (!selectAllAccounts && selectedAccountIds.length === 0)}
            >
              {isExecuting ? "Executing..." : "Run Check"}
            </button>
          </form>
        )}

        {isExecuting ? <LoadingState /> : null}
        {error ? <p className="form-error" role="alert">{error}</p> : null}
      </section>

      {result ? (
        <section className="ops-glass-panel checks-result" aria-label="Single check output">
          <p className="checks-meta">Execution time: {result.execution_time_seconds}s</p>
          {Object.entries(result.consolidated_outputs).map(([custId, output]) => {
            const custName = customers.find((c) => c.id === custId)?.display_name ?? custId
            return <CopyableOutput key={custId} title={`${custName} — Output`} text={output} />
          })}
          {result.results.map((item, index) => (
            <article key={`${item.account.id}-${item.check_name}-${index}`} className="checks-result-row">
              <header>
                <h2>{item.account.display_name} ({item.account.profile_name})</h2>
                <StatusBadge status={item.status} />
              </header>
              <p>{item.summary}</p>
              <CopyableOutput title={`${item.check_name} Output`} text={item.output || item.summary} />
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
