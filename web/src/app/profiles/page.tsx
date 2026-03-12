import { useEffect, useMemo, useState } from "react"

import { addAccount, listCustomers } from "../../api/customers"
import { toUserMessage } from "../../api/client"
import { detectProfiles } from "../../api/profiles"
import { LoadingState } from "../../components/common/LoadingState"
import type { Customer } from "../../types/api"

type DetectionState = {
  all_profiles: string[]
  mapped_profiles: string[]
  unmapped_profiles: string[]
}

export default function ProfilesPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [quickAddCustomerId, setQuickAddCustomerId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isQuickAdding, setIsQuickAdding] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState<DetectionState | null>(null)

  useEffect(() => {
    let isMounted = true

    const loadCustomersData = async () => {
      try {
        const rows = await listCustomers()
        if (!isMounted) {
          return
        }

        setCustomers(rows)
        if (rows[0]) {
          setQuickAddCustomerId(rows[0].id)
        }
      } catch {
        // Keep page usable even if customer load fails.
      }
    }

    void loadCustomersData()

    return () => {
      isMounted = false
    }
  }, [])

  const onScan = async () => {
    setIsLoading(true)
    setError("")

    try {
      const rows = await detectProfiles()
      setResult(rows)
    } catch (scanError) {
      setError(toUserMessage(scanError, "Failed to scan AWS profiles."))
    } finally {
      setIsLoading(false)
    }
  }

  const mappedToCustomer = useMemo(() => {
    const profileMap = new Map<string, string>()
    for (const customer of customers) {
      for (const account of customer.accounts) {
        profileMap.set(account.profile_name, customer.display_name)
      }
    }
    return profileMap
  }, [customers])

  const onQuickAdd = async (profileName: string) => {
    if (!quickAddCustomerId) {
      setError("Select customer for quick-add first.")
      return
    }

    try {
      setIsQuickAdding(true)
      await addAccount(quickAddCustomerId, {
        profile_name: profileName,
        display_name: profileName,
      })

      const refreshedCustomers = await listCustomers()
      setCustomers(refreshedCustomers)

      setResult((current) => {
        if (!current) {
          return current
        }

        return {
          ...current,
          mapped_profiles: Array.from(new Set([...current.mapped_profiles, profileName])),
          unmapped_profiles: current.unmapped_profiles.filter((profile) => profile !== profileName),
        }
      })
    } catch (quickAddError) {
      setError(toUserMessage(quickAddError, "Failed to add profile to customer."))
    } finally {
      setIsQuickAdding(false)
    }
  }

  return (
    <main className="ops-page profiles-page" aria-labelledby="profiles-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="profiles-title">Profile Detection</h1>
        <p>Scan local AWS config profiles and detect mapping coverage.</p>
      </section>

      <section className="ops-glass-panel checks-form-panel">
        <label htmlFor="profile-quick-add-customer">Quick Add Customer</label>
        <select
          id="profile-quick-add-customer"
          className="ops-select"
          value={quickAddCustomerId}
          onChange={(event) => setQuickAddCustomerId(event.target.value)}
          disabled={isLoading || isQuickAdding}
        >
          <option value="">Select customer</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.display_name} ({customer.name})
            </option>
          ))}
        </select>

        <button type="button" className="ops-button" onClick={onScan} disabled={isLoading}>
          {isLoading ? "Scanning..." : "Scan AWS Profiles"}
        </button>
      </section>

      {isLoading ? <LoadingState title="Scanning profiles..." /> : null}
      {isQuickAdding ? (
        <LoadingState title="Adding profile..." detail="Updating customer account mapping." />
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="profiles-grid">
          <article className="ops-glass-panel checks-form-panel">
            <h2>All Profiles</h2>
            <ul>
              {result.all_profiles.map((profile) => (
                <li key={profile}>{profile}</li>
              ))}
            </ul>
          </article>

          <article className="ops-glass-panel checks-form-panel">
            <h2>Mapped Profiles</h2>
            <ul>
              {result.mapped_profiles.map((profile) => (
                <li key={profile}>
                  {profile}{" "}
                  {mappedToCustomer.get(profile) ? `- ${mappedToCustomer.get(profile)}` : ""}
                </li>
              ))}
            </ul>
          </article>

          <article className="ops-glass-panel checks-form-panel">
            <h2>Unmapped Profiles</h2>
            <ul>
              {result.unmapped_profiles.map((profile) => (
                <li key={profile} className="profiles-unmapped-item">
                  <span>{profile}</span>
                  <button
                    type="button"
                    className="ops-button"
                    onClick={() => onQuickAdd(profile)}
                    disabled={isQuickAdding || !quickAddCustomerId}
                  >
                    Add to Customer
                  </button>
                </li>
              ))}
            </ul>
          </article>
        </section>
      ) : null}
    </main>
  )
}
