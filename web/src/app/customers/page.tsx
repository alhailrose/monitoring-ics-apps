import { useEffect, useMemo, useState, type FormEvent } from "react"

import {
  addAccount,
  createCustomer,
  deleteAccount,
  deleteCustomer,
  listCustomers,
  updateAccount,
  updateCustomer,
} from "../../api/customers"
import { toUserMessage } from "../../api/client"
import { LoadingState } from "../../components/common/LoadingState"
import { StatusBadge } from "../../components/common/StatusBadge"
import type { Customer } from "../../types/api"

const pickExistingOrFirst = (rows: Customer[], currentId: string): string => {
  if (rows.some((customer) => customer.id === currentId)) {
    return currentId
  }
  return rows[0]?.id ?? ""
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isWorking, setIsWorking] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const [name, setName] = useState("")
  const [displayName, setDisplayName] = useState("")

  const [targetCustomerId, setTargetCustomerId] = useState("")
  const [profileName, setProfileName] = useState("")
  const [accountDisplayName, setAccountDisplayName] = useState("")

  const [botCustomerId, setBotCustomerId] = useState("")
  const [botWebhook, setBotWebhook] = useState("")
  const [botChannel, setBotChannel] = useState("")
  const [botEnabled, setBotEnabled] = useState(false)

  const selectedBotCustomer = useMemo(
    () => customers.find((customer) => customer.id === botCustomerId) ?? null,
    [botCustomerId, customers],
  )

  const hydrateBotForm = (customer: Customer | null) => {
    setBotWebhook(customer?.slack_webhook_url ?? "")
    setBotChannel(customer?.slack_channel ?? "")
    setBotEnabled(Boolean(customer?.slack_enabled))
  }

  const loadCustomers = async () => {
    setIsLoading(true)
    setError("")

    try {
      const rows = await listCustomers()
      setCustomers(rows)

      setTargetCustomerId((current) => pickExistingOrFirst(rows, current))
      setBotCustomerId((current) => pickExistingOrFirst(rows, current))
    } catch (loadError) {
      setError(toUserMessage(loadError, "Failed to load customers."))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadCustomers()
  }, [])

  useEffect(() => {
    hydrateBotForm(selectedBotCustomer)
  }, [selectedBotCustomer])

  const onCreateCustomer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    try {
      setIsWorking(true)
      setError("")
      setNotice("")

      await createCustomer({
        name: name.trim(),
        display_name: displayName.trim(),
        slack_enabled: false,
      })

      setName("")
      setDisplayName("")
      setNotice("Customer created.")
      await loadCustomers()
    } catch (createError) {
      setError(toUserMessage(createError, "Failed to create customer."))
    } finally {
      setIsWorking(false)
    }
  }

  const onAddAccount = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!targetCustomerId) {
      setError("Target customer is required.")
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")

      await addAccount(targetCustomerId, {
        profile_name: profileName.trim(),
        display_name: accountDisplayName.trim(),
      })

      setProfileName("")
      setAccountDisplayName("")
      setNotice("Account added.")
      await loadCustomers()
    } catch (addError) {
      setError(toUserMessage(addError, "Failed to add account."))
    } finally {
      setIsWorking(false)
    }
  }

  const onSaveBotMapping = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!botCustomerId) {
      setError("Bot customer is required.")
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")

      await updateCustomer(botCustomerId, {
        slack_webhook_url: botWebhook.trim() || null,
        slack_channel: botChannel.trim() || null,
        slack_enabled: botEnabled,
      })

      setNotice("Bot mapping updated.")
      await loadCustomers()
    } catch (botError) {
      setError(toUserMessage(botError, "Failed to update bot mapping."))
    } finally {
      setIsWorking(false)
    }
  }

  const onEditCustomer = async (customer: Customer) => {
    const nextDisplayName = window.prompt("New display name", customer.display_name)?.trim()
    if (!nextDisplayName || nextDisplayName === customer.display_name) {
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")
      await updateCustomer(customer.id, { display_name: nextDisplayName })
      setNotice("Customer updated.")
      await loadCustomers()
    } catch (editError) {
      setError(toUserMessage(editError, "Failed to update customer."))
    } finally {
      setIsWorking(false)
    }
  }

  const onDeleteCustomer = async (customer: Customer) => {
    if (!window.confirm(`Delete customer ${customer.display_name}?`)) {
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")
      await deleteCustomer(customer.id)
      setNotice("Customer deleted.")
      await loadCustomers()
    } catch (deleteError) {
      setError(toUserMessage(deleteError, "Failed to delete customer."))
    } finally {
      setIsWorking(false)
    }
  }

  const onRenameAccount = async (accountId: string, currentDisplayName: string) => {
    const nextDisplayName = window.prompt("New account display name", currentDisplayName)?.trim()
    if (!nextDisplayName || nextDisplayName === currentDisplayName) {
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")
      await updateAccount(accountId, { display_name: nextDisplayName })
      setNotice("Account updated.")
      await loadCustomers()
    } catch (editError) {
      setError(toUserMessage(editError, "Failed to update account."))
    } finally {
      setIsWorking(false)
    }
  }

  const onToggleAccountActive = async (accountId: string, currentActive: boolean) => {
    try {
      setIsWorking(true)
      setError("")
      setNotice("")
      await updateAccount(accountId, { is_active: !currentActive })
      setNotice("Account status updated.")
      await loadCustomers()
    } catch (toggleError) {
      setError(toUserMessage(toggleError, "Failed to update account status."))
    } finally {
      setIsWorking(false)
    }
  }

  const onDeleteAccount = async (accountId: string, displayNameValue: string) => {
    if (!window.confirm(`Delete account ${displayNameValue}?`)) {
      return
    }

    try {
      setIsWorking(true)
      setError("")
      setNotice("")
      await deleteAccount(accountId)
      setNotice("Account deleted.")
      await loadCustomers()
    } catch (deleteError) {
      setError(toUserMessage(deleteError, "Failed to delete account."))
    } finally {
      setIsWorking(false)
    }
  }

  return (
    <main className="ops-page customers-page" aria-labelledby="customers-page-title">
      <section className="ops-glass-panel checks-header customer-header">
        <h1 id="customers-page-title">Customer Management</h1>
        <p>Manage customers, account mappings, and bot notification routing.</p>
      </section>

      <section className="customer-sections">
        <section className="ops-glass-panel checks-form-panel customer-panel">
          <h2>Add Customer</h2>
          <form className="checks-form" onSubmit={onCreateCustomer}>
            <label htmlFor="customer-name">Name</label>
            <input
              id="customer-name"
              className="ops-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="aryanoble"
              required
              disabled={isWorking}
            />

            <label htmlFor="customer-display-name">Display Name</label>
            <input
              id="customer-display-name"
              className="ops-input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Aryanoble"
              required
              disabled={isWorking}
            />

            <button type="submit" className="ops-button" disabled={isWorking}>Add Customer</button>
          </form>
        </section>

        <section className="ops-glass-panel checks-form-panel customer-panel">
          <h2>Add Account</h2>
          <form className="checks-form" onSubmit={onAddAccount}>
            <label htmlFor="target-customer">Target Customer</label>
            <select
              id="target-customer"
              className="ops-select"
              value={targetCustomerId}
              onChange={(event) => setTargetCustomerId(event.target.value)}
              disabled={isWorking || customers.length === 0}
              required
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

            <label htmlFor="profile-name">Profile Name</label>
            <input
              id="profile-name"
              className="ops-input"
              value={profileName}
              onChange={(event) => setProfileName(event.target.value)}
              placeholder="aws-profile-name"
              required
              disabled={isWorking}
            />

            <label htmlFor="account-display-name">Account Display Name</label>
            <input
              id="account-display-name"
              className="ops-input"
              value={accountDisplayName}
              onChange={(event) => setAccountDisplayName(event.target.value)}
              placeholder="Production"
              required
              disabled={isWorking}
            />

            <button type="submit" className="ops-button" disabled={isWorking || !targetCustomerId}>Add Account</button>
          </form>
        </section>

        <section className="ops-glass-panel checks-form-panel customer-panel">
          <h2>Bot Mapping (Slack)</h2>
          <form className="checks-form" onSubmit={onSaveBotMapping}>
            <label htmlFor="bot-customer">Bot Customer</label>
            <select
              id="bot-customer"
              className="ops-select"
              value={botCustomerId}
              onChange={(event) => setBotCustomerId(event.target.value)}
              disabled={isWorking || customers.length === 0}
              required
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

            <label htmlFor="bot-webhook-url">Bot Webhook URL</label>
            <input
              id="bot-webhook-url"
              className="ops-input"
              value={botWebhook}
              onChange={(event) => setBotWebhook(event.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              disabled={isWorking}
            />

            <label htmlFor="bot-channel">Bot Channel</label>
            <input
              id="bot-channel"
              className="ops-input"
              value={botChannel}
              onChange={(event) => setBotChannel(event.target.value)}
              placeholder="#monitoring"
              disabled={isWorking}
            />

            <label className="checks-inline-checkbox" htmlFor="bot-enabled">
              <input
                id="bot-enabled"
                type="checkbox"
                checked={botEnabled}
                onChange={(event) => setBotEnabled(event.target.checked)}
                disabled={isWorking}
              />
              Bot Enabled
            </label>

            <button type="submit" className="ops-button" disabled={isWorking || !botCustomerId}>Save Bot Mapping</button>
          </form>
        </section>
      </section>

      {isLoading ? <LoadingState title="Loading customers..." /> : null}
      {isWorking ? <LoadingState title="Saving..." detail="Applying changes to backend." /> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {notice ? <p className="form-notice" role="status">{notice}</p> : null}

      {!isLoading ? (
        <section className="ops-glass-panel checks-result" aria-label="Customer list">
          {customers.length === 0 ? <p>No customers yet.</p> : null}

          {customers.map((customer) => (
            <article key={customer.id} className="checks-result-row customer-card">
              <header>
                <h2>{customer.display_name} ({customer.name})</h2>
                <StatusBadge status={customer.slack_enabled ? "OK" : "NO_DATA"} />
              </header>

              <div className="customer-meta">
                <p>Accounts: {customer.accounts.length}</p>
                <p>Bot Channel: {customer.slack_channel || "-"}</p>
              </div>

              <div className="checks-actions">
                <button type="button" className="ops-button" onClick={() => onEditCustomer(customer)} disabled={isWorking}>
                  Edit Customer
                </button>
                <button type="button" className="ops-button" onClick={() => onDeleteCustomer(customer)} disabled={isWorking}>
                  Delete Customer
                </button>
              </div>

              {customer.accounts.map((account) => (
                <div key={account.id} className="checks-account-row">
                  <p>
                    {account.display_name} ({account.profile_name})
                    {account.account_id ? ` | ${account.account_id}` : ""}
                  </p>
                  <div className="checks-actions">
                    <button
                      type="button"
                      className="ops-button"
                      onClick={() => onRenameAccount(account.id, account.display_name)}
                      disabled={isWorking}
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      className="ops-button"
                      onClick={() => onToggleAccountActive(account.id, account.is_active)}
                      disabled={isWorking}
                    >
                      {account.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button
                      type="button"
                      className="ops-button"
                      onClick={() => onDeleteAccount(account.id, account.display_name)}
                      disabled={isWorking}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
