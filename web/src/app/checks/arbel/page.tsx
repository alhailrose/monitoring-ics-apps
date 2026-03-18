import { useEffect, useMemo, useState } from "react"

import { executeChecks } from "../../../api/checks"
import { toUserMessage } from "../../../api/client"
import { listCustomers } from "../../../api/customers"
import { CopyableOutput } from "../../../components/common/CopyableOutput"
import { LoadingState } from "../../../components/common/LoadingState"
import { StatusBadge } from "../../../components/common/StatusBadge"
import type { Account, BackupOverview, Customer, ExecuteCheckResponse } from "../../../types/api"
import {
  MENUS,
  WINDOW_OPTIONS,
  getAlarmNames,
  getDefaultConsolidatedOutput,
  hasAlarms,
  pickArbelCustomer,
  type ArbelMenu,
  type MenuConfig,
} from "../../../features/arbel/menu"

export const VISIBLE_PROFILE_STORAGE_KEY = "arbel_visible_profiles"
const PROFILE_MODES = ["rds", "ec2"] as const
type ProfileMode = (typeof PROFILE_MODES)[number]

type VisibleProfileState = Record<ProfileMode, string[]>

const defaultVisibleProfileState: VisibleProfileState = {
  rds: [],
  ec2: [],
}

const isProfileMode = (menu: ArbelMenu): menu is ProfileMode =>
  PROFILE_MODES.includes(menu as ProfileMode)

const sanitizeProfileIds = (ids: string[], allowedIds: Set<string>): string[] => {
  const seen = new Set<string>()
  const next: string[] = []
  ids.forEach((id) => {
    if (!allowedIds.has(id) || seen.has(id)) return
    seen.add(id)
    next.push(id)
  })
  return next
}

const readVisibleProfilesFromStorage = (): Partial<VisibleProfileState> => {
  if (typeof window === "undefined") return {}
  try {
    const raw = window.localStorage.getItem(VISIBLE_PROFILE_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Partial<Record<string, string[]>>
    const result: Partial<VisibleProfileState> = {}
    PROFILE_MODES.forEach((mode) => {
      const list = parsed[mode]
      if (Array.isArray(list)) {
        result[mode] = list.filter((id): id is string => typeof id === "string")
      }
    })
    return result
  } catch {
    return {}
  }
}

const writeVisibleProfilesToStorage = (state: VisibleProfileState) => {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(VISIBLE_PROFILE_STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Ignore storage errors
  }
}

type BackupSummaryView = {
  allSuccess: boolean
  total: number
  success: number
  failed: number
  failedAccounts: Array<{ displayName: string; profile: string }>
}

const buildBackupSummaryFromResults = (results: ExecuteCheckResponse["results"]): BackupSummaryView => {
  const failedAccounts = results
    .filter((item) => item.status !== "OK")
    .map((item) => ({
      displayName: item.account.display_name,
      profile: item.account.profile_name,
    }))

  const total = results.length
  const failed = failedAccounts.length
  const success = Math.max(total - failed, 0)

  return {
    allSuccess: total > 0 && failed === 0,
    total,
    success,
    failed,
    failedAccounts,
  }
}

const buildBackupSummary = (response: ExecuteCheckResponse): BackupSummaryView => {
  const fallback = buildBackupSummaryFromResults(response.results)
  const overview = Object.values(response.backup_overviews)[0] as BackupOverview | undefined

  if (!overview) return fallback

  const total = typeof overview.total_accounts === "number" ? overview.total_accounts : fallback.total
  const success =
    typeof overview.ok_accounts_count === "number" ? overview.ok_accounts_count : fallback.success
  const failed =
    typeof overview.problem_accounts_count === "number"
      ? overview.problem_accounts_count
      : Math.max(total - success, fallback.failed)

  const overviewFailedAccounts = Array.isArray(overview.problem_accounts)
    ? overview.problem_accounts
        .map((account) => {
          const displayName =
            typeof account.display_name === "string" && account.display_name.length > 0
              ? account.display_name
              : "Unknown"
          const profile = typeof account.profile === "string" ? account.profile : ""
          return { displayName, profile }
        })
        .filter((account) => account.displayName !== "Unknown" || account.profile !== "")
    : []

  return {
    allSuccess: typeof overview.all_success === "boolean" ? overview.all_success : failed === 0,
    total,
    success,
    failed,
    failedAccounts: overviewFailedAccounts.length > 0 ? overviewFailedAccounts : fallback.failedAccounts,
  }
}

export default function ArbelCheckPage() {
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  const [activeMenu, setActiveMenu] = useState<ArbelMenu | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  // Per-menu state
  const [visibleProfiles, setVisibleProfiles] = useState<VisibleProfileState>(defaultVisibleProfileState)
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([])
  const [selectAll, setSelectAll] = useState(true)
  const [profileSelections, setProfileSelections] = useState<Record<ProfileMode, string>>({
    rds: "",
    ec2: "",
  })
  const [windowHours, setWindowHours] = useState(12)
  const [sendSlack, setSendSlack] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [result, setResult] = useState<ExecuteCheckResponse | null>(null)
  // Alarm menu: { accountId: Set<alarmName> } — empty = account not participating
  const [selectedAlarms, setSelectedAlarms] = useState<Record<string, Set<string>>>({})
  // Track which alarm accordion cards are expanded
  const [expandedAlarmAccounts, setExpandedAlarmAccounts] = useState<Set<string>>(new Set())

  const backupSummary = useMemo(() => {
    if (!result || activeMenu !== "backup") return null
    const hasBackupResults = result.results.some((item) => item.check_name === "backup")
    if (!hasBackupResults && Object.keys(result.backup_overviews).length === 0) return null
    return buildBackupSummary(result)
  }, [activeMenu, result])

  const accounts = useMemo(() => {
    if (!customer) return []
    return customer.accounts.filter((a) => a.is_active)
  }, [customer])

  useEffect(() => {
    if (!customer) return
    const stored = readVisibleProfilesFromStorage()
    const allowedIds = new Set(accounts.map((a) => a.id))
    const nextState: VisibleProfileState = { ...defaultVisibleProfileState }
    PROFILE_MODES.forEach((mode) => {
      const defaults = accounts.map((a) => a.id)
      const storedIds = stored[mode]
      const sanitized = storedIds?.length
        ? sanitizeProfileIds(storedIds, allowedIds)
        : defaults
      nextState[mode] = sanitized.length > 0 ? sanitized : defaults
    })
    setVisibleProfiles(nextState)
  }, [customer, accounts])

  useEffect(() => {
    if (!activeMenu || !isProfileMode(activeMenu)) return
    setSelectedAccountIds(visibleProfiles[activeMenu])
  }, [activeMenu, visibleProfiles])

  useEffect(() => {
    if (!activeMenu || !isProfileMode(activeMenu)) return
    setSelectedAccountIds((current) => {
      const visibleIds = new Set(visibleProfiles[activeMenu])
      const filtered = current.filter((id) => visibleIds.has(id))
      if (selectAll) return visibleProfiles[activeMenu]
      return filtered
    })
  }, [visibleProfiles, activeMenu, selectAll])

  useEffect(() => {
    if (!customer) return
    writeVisibleProfilesToStorage(visibleProfiles)
  }, [visibleProfiles, customer])

  // For alarm verification, only show accounts that have alarm_names
  const alarmAccounts = useMemo(() => accounts.filter(hasAlarms), [accounts])

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setIsLoading(true)
      setError("")
      try {
        const rows = await listCustomers()
        if (!mounted) return
        const arbel = pickArbelCustomer(rows)
        if (!arbel) {
          setError("Aryanoble customer not found.")
          return
        }
        setCustomer(arbel)
      } catch (e) {
        if (mounted) setError(toUserMessage(e, "Failed to load."))
      } finally {
        if (mounted) setIsLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [reloadKey])

  const onToggleMenu = (key: ArbelMenu) => {
    if (activeMenu === key) {
      setActiveMenu(null)
      if (key === "alarm") {
        setSelectedAlarms({})
        setExpandedAlarmAccounts(new Set())
      }
      return
    }
    setActiveMenu(key)
    setResult(null)
    setError("")
    setSendSlack(false)
    setSelectAll(true)
    setWindowHours(12)

    if (key === "alarm") {
      setSelectedAlarms({})
      setExpandedAlarmAccounts(new Set())
    } else if (isProfileMode(key)) {
      const nextIds = visibleProfiles[key]
      setSelectedAccountIds(nextIds)
    } else {
      setSelectedAccountIds(accounts.map((a) => a.id))
    }
  }

  const onToggleSelectAll = (checked: boolean) => {
    setSelectAll(checked)
    if (checked) {
      if (activeMenu && isProfileMode(activeMenu)) {
        setSelectedAccountIds(visibleProfiles[activeMenu])
      } else {
        setSelectedAccountIds(accounts.map((a) => a.id))
      }
    } else {
      setSelectedAccountIds([])
    }
  }

  const toggleAccount = (id: string) => {
    setSelectedAccountIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  }

  const onRun = async (menu: MenuConfig) => {
    if (!customer) return

    setIsExecuting(true)
    setError("")
    setResult(null)

    let accountIds: string[] | null = null
    let checkParams: Record<string, unknown> | null = null

    if (menu.key === "alarm") {
      // Build per-account alarm map; skip accounts with no alarms selected
      const accountAlarmNames: Record<string, string[]> = {}
      for (const [accountId, alarms] of Object.entries(selectedAlarms)) {
        if (alarms.size > 0) {
          accountAlarmNames[accountId] = [...alarms]
        }
      }
      const participatingIds = Object.keys(accountAlarmNames)
      if (participatingIds.length === 0) {
        setError("Select at least one alarm.")
        setIsExecuting(false)
        return
      }
      accountIds = participatingIds
      checkParams = { account_alarm_names: accountAlarmNames }
    } else {
      if (selectedAccountIds.length === 0) {
        setError("Select at least one account.")
        setIsExecuting(false)
        return
      }
      accountIds = selectAll ? null : selectedAccountIds
      if (menu.key === "rds") {
        checkParams = { window_hours: windowHours, section_scope: "rds" }
      }
      if (menu.key === "ec2") {
        checkParams = { window_hours: windowHours, section_scope: "ec2" }
      }
    }

    try {
      const run = await executeChecks({
        customer_ids: [customer.id],
        mode: "single",
        check_name: menu.checkName,
        account_ids: accountIds,
        send_slack: sendSlack,
        check_params: checkParams,
      })
      setResult(run)
    } catch (e) {
      setError(toUserMessage(e, `Failed to execute ${menu.label}.`))
    } finally {
      setIsExecuting(false)
    }
  }

  const toggleAlarm = (accountId: string, alarmName: string) => {
    setSelectedAlarms((cur) => {
      const next = { ...cur }
      const set = new Set(cur[accountId] ?? [])
      if (set.has(alarmName)) {
        set.delete(alarmName)
      } else {
        set.add(alarmName)
      }
      next[accountId] = set
      return next
    })
  }

  const selectAllAlarmsForAccount = (accountId: string, alarmNames: string[]) => {
    setSelectedAlarms((cur) => ({ ...cur, [accountId]: new Set(alarmNames) }))
  }

  const clearAlarmsForAccount = (accountId: string) => {
    setSelectedAlarms((cur) => ({ ...cur, [accountId]: new Set() }))
  }

  const toggleAlarmAccountExpanded = (accountId: string) => {
    setExpandedAlarmAccounts((cur) => {
      const next = new Set(cur)
      if (next.has(accountId)) {
        next.delete(accountId)
      } else {
        next.add(accountId)
      }
      return next
    })
  }

  const renderAlarmSelector = () => {
    if (alarmAccounts.length === 0) {
      return (
        <p className="checks-help">
          No accounts have alarm_names configured. Run seed_alarms script first.
        </p>
      )
    }

    return (
      <div className="arbel-alarm-accordion">
        {alarmAccounts.map((account) => {
          const alarmNames = getAlarmNames(account)
          const selected = selectedAlarms[account.id] ?? new Set<string>()
          const isExpanded = expandedAlarmAccounts.has(account.id)
          const selectedCount = selected.size
          const allSelected = selectedCount === alarmNames.length && alarmNames.length > 0
          const someSelected = selectedCount > 0 && selectedCount < alarmNames.length

          return (
            <div key={account.id} className="arbel-alarm-account-card">
              <div className="arbel-alarm-account-header">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected
                  }}
                  onChange={() => {
                    if (allSelected || someSelected) {
                      clearAlarmsForAccount(account.id)
                    } else {
                      selectAllAlarmsForAccount(account.id, alarmNames)
                    }
                  }}
                  disabled={isExecuting}
                />
                <span
                  className="arbel-alarm-account-label"
                  onClick={() => toggleAlarmAccountExpanded(account.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && toggleAlarmAccountExpanded(account.id)}
                >
                  {account.display_name} ({account.profile_name})
                </span>
                <span className="arbel-alarm-count-badge">
                  {selectedCount}/{alarmNames.length} selected
                </span>
                <div className="arbel-alarm-account-actions">
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => selectAllAlarmsForAccount(account.id, alarmNames)}
                    disabled={isExecuting}
                  >
                    all
                  </button>
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => clearAlarmsForAccount(account.id)}
                    disabled={isExecuting}
                  >
                    none
                  </button>
                  <button
                    type="button"
                    className="arbel-alarm-action-btn"
                    onClick={() => toggleAlarmAccountExpanded(account.id)}
                  >
                    {isExpanded ? "▲" : "▼"}
                  </button>
                </div>
              </div>

              {isExpanded ? (
                <div className="arbel-alarm-list">
                  {alarmNames.map((name) => (
                    <label key={name} className="arbel-alarm-item">
                      <input
                        type="checkbox"
                        checked={selected.has(name)}
                        onChange={() => toggleAlarm(account.id, name)}
                        disabled={isExecuting}
                      />
                      {name}
                    </label>
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    )
  }

  const renderAccountSelector = (pool: Account[]) => (
    <div className="arbel-accounts">
      <div style={{ marginBottom: "1rem" }}>
        <label className="ops-toggle-card">
          <input
            type="checkbox"
            checked={selectAll}
            onChange={(e) => onToggleSelectAll(e.target.checked)}
            disabled={isExecuting}
          />
          Select All ({pool.length})
        </label>
      </div>
      <div className="ops-checkbox-grid">
        {pool.length === 0 ? <p className="checks-help">No accounts available.</p> : null}
        {pool.map((account) => (
          <label
            key={account.id}
            className="ops-checkbox-card"
            style={selectAll ? { opacity: 0.5, pointerEvents: "none" } : {}}
          >
            <input
              type="checkbox"
              checked={selectedAccountIds.includes(account.id)}
              onChange={() => toggleAccount(account.id)}
              disabled={selectAll || isExecuting}
            />
            <div className="ops-checkbox-label">
              {account.display_name}
              <span className="ops-checkbox-meta">{account.profile_name}</span>
            </div>
          </label>
        ))}
      </div>
    </div>
  )

  const renderProfileManager = (menu: MenuConfig, pool: Account[]) => {
    if (!isProfileMode(menu.key)) return null
    const key = menu.key
    const visibleIds = visibleProfiles[key]
    const visibleAccounts = pool.filter((account) => visibleIds.includes(account.id))
    const availableAccounts = pool.filter((account) => !visibleIds.includes(account.id))
    const availableOptions = availableAccounts.map((account) => (
      <option key={account.id} value={account.id}>
        {account.display_name} ({account.profile_name})
      </option>
    ))

    const selectedOption = profileSelections[key]

    const onChangeSelect = (value: string) => {
      setProfileSelections((current) => ({ ...current, [key]: value }))
    }

    const addProfile = () => {
      if (!selectedOption) return
      setVisibleProfiles((current) => {
        const next = { ...current }
        const existing = new Set(next[key])
        if (existing.has(selectedOption)) return current
        next[key] = [...next[key], selectedOption]
        return next
      })
      setProfileSelections((current) => ({ ...current, [key]: "" }))
    }

    const removeProfile = (accountId: string) => {
      setVisibleProfiles((current) => {
        const next = { ...current }
        next[key] = next[key].filter((id) => id !== accountId)
        return next
      })
    }

    const resetProfiles = () => {
      setVisibleProfiles((current) => {
        const next = { ...current }
        next[key] = pool.map((account) => account.id)
        return next
      })
      setProfileSelections((current) => ({ ...current, [key]: "" }))
    }

    return (
      <section className="arbel-profile-manager" aria-label="Kelola Profil">
        <div className="arbel-profile-header">
          <div>
            <h3>Kelola Profil</h3>
            <p>Atur profil yang ditampilkan pada menu ini.</p>
          </div>
          <span
            className="arbel-profile-count"
            data-testid={`profile-count-${menu.key}`}
          >
            Ditampilkan {visibleAccounts.length}/{pool.length}
          </span>
        </div>

        <div className="arbel-profile-actions">
          <label className="sr-only" htmlFor={`profile-select-${menu.key}`}>
            Tambah profil
          </label>
          <select
            id={`profile-select-${menu.key}`}
            className="ops-select"
            value={selectedOption}
            onChange={(e) => onChangeSelect(e.target.value)}
            disabled={isExecuting || availableOptions.length === 0}
          >
            <option value="">Pilih akun</option>
            {availableOptions}
          </select>
          <button
            type="button"
            className="ops-button"
            onClick={addProfile}
            disabled={isExecuting || !selectedOption}
          >
            Tambah ke daftar
          </button>
          <button
            type="button"
            className="ops-button secondary"
            onClick={resetProfiles}
            disabled={isExecuting || pool.length === 0}
          >
            Reset ke default
          </button>
        </div>

        <div className="arbel-profile-chips">
          {visibleAccounts.length === 0 ? (
            <p className="checks-help">Tidak ada profil ditampilkan. Tambah profil untuk memulai.</p>
          ) : (
            visibleAccounts.map((account) => (
              <span key={account.id} className="arbel-profile-chip">
                <span aria-label="profil-active-chip">
                  {account.display_name}
                  <span className="arbel-profile-chip-meta">{account.profile_name}</span>
                </span>
                <button
                  type="button"
                  onClick={() => removeProfile(account.id)}
                  disabled={isExecuting}
                >
                  Hapus dari daftar
                </button>
              </span>
            ))
          )}
        </div>
      </section>
    )
  }

  const renderSubMenu = (menu: MenuConfig) => {
    const profilePool = accounts
    const visibleAccounts = isProfileMode(menu.key)
      ? profilePool.filter((account) => visibleProfiles[menu.key as ProfileMode].includes(account.id))
      : profilePool

    return (
      <div className="arbel-submenu">
        {menu.key === "alarm" ? renderAlarmSelector() : (
          <>
            {renderProfileManager(menu, profilePool)}
            {renderAccountSelector(visibleAccounts)}
          </>
        )}

        {menu.key === "rds" || menu.key === "ec2" ? (
          <div className="arbel-option-row" style={{ marginTop: "1rem" }}>
            <label htmlFor="arbel-window" className="form-label">
              Monitoring Window
            </label>
            <select
              id="arbel-window"
              className="ops-select"
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              disabled={isExecuting}
            >
              {WINDOW_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div className="arbel-run-row" style={{ marginTop: "1rem" }}>
          <label className="ops-toggle-card">
            <input
              type="checkbox"
              checked={sendSlack}
              onChange={(e) => setSendSlack(e.target.checked)}
              disabled={isExecuting}
            />
            Send Alert to Slack
          </label>
          <button
            className="ops-button"
            type="button"
            onClick={() => onRun(menu)}
            disabled={
              isExecuting ||
              (menu.key === "alarm"
                ? Object.values(selectedAlarms).every((s) => s.size === 0)
                : selectedAccountIds.length === 0)
            }
          >
            {isExecuting ? "EXECUTING..." : `RUN ${menu.label.toUpperCase()}`}
          </button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <main className="ops-page checks-page" aria-labelledby="arbel-title">
        <section className="ops-glass-panel checks-header">
          <h1 id="arbel-title">Arbel Check</h1>
          <p>Aryanoble monitoring suite</p>
        </section>
        <section className="ops-glass-panel checks-form-panel">
          <LoadingState title="Loading Aryanoble configuration..." />
        </section>
      </main>
    )
  }

  if (!customer) {
    return (
      <main className="ops-page checks-page" aria-labelledby="arbel-title">
        <section className="ops-glass-panel checks-header">
          <h1 id="arbel-title">Arbel Check</h1>
          <p>Aryanoble monitoring suite</p>
        </section>

        <section className="ops-glass-panel checks-form-panel" aria-live="polite">
          <p className="form-error" role="alert">
            {error || "Aryanoble customer not found."}
          </p>
          <button
            type="button"
            className="ops-button"
            onClick={() => setReloadKey((current) => current + 1)}
            disabled={isExecuting}
          >
            Retry Load
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="ops-page checks-page" aria-labelledby="arbel-title">
      <section className="ops-glass-panel checks-header">
        <h1 id="arbel-title">Arbel Check</h1>
        <p>
          {customer
            ? `${customer.display_name} — ${accounts.length} active accounts`
            : "Aryanoble monitoring suite"}
        </p>
      </section>

      <div className="arbel-menu-grid">
        {MENUS.map((menu) => {
          const isOpen = activeMenu === menu.key
          return (
            <section
              key={menu.key}
              className={`ops-glass-panel arbel-menu-card${isOpen ? " arbel-menu-open" : ""}`}
            >
              <button
                type="button"
                className="arbel-menu-header"
                onClick={() => onToggleMenu(menu.key)}
                aria-expanded={isOpen}
              >
                <div>
                  <h2>{menu.label}</h2>
                  <p>{menu.description}</p>
                </div>
                <span className="arbel-chevron">{isOpen ? "\u25B2" : "\u25BC"}</span>
              </button>

              {isOpen ? renderSubMenu(menu) : null}
            </section>
          )
        })}
      </div>

      {error ? (
        <section className="ops-glass-panel">
          <p className="form-error" role="alert">
            {error}
          </p>
        </section>
      ) : null}

      {isExecuting ? (
        <section className="ops-glass-panel">
          <LoadingState />
        </section>
      ) : null}

      {result ? (
        <section className="ops-glass-panel checks-result" aria-label="Check output">
          <p className="checks-meta">Execution time: {result.execution_time_seconds}s</p>
          <CopyableOutput
            title="Output"
            text={getDefaultConsolidatedOutput(result.consolidated_outputs)}
          />

          {backupSummary ? (
            <section
              className={`arbel-backup-summary${backupSummary.allSuccess ? " is-success" : " is-failed"}`}
              aria-label="Backup summary"
            >
              <p className="arbel-backup-summary-status">
                {backupSummary.allSuccess ? "Semua sukses" : "Ada gagal"}
              </p>
              <ul className="arbel-backup-summary-counts">
                <li>Total: {backupSummary.total}</li>
                <li>Sukses: {backupSummary.success}</li>
                <li>Gagal: {backupSummary.failed}</li>
              </ul>

              {backupSummary.failed > 0 ? (
                <div className="arbel-backup-summary-failed">
                  <p>Akun gagal:</p>
                  <ul>
                    {backupSummary.failedAccounts.map((account, index) => (
                      <li key={`${account.displayName}-${account.profile}-${index}`}>
                        {account.profile
                          ? `${account.displayName} (${account.profile})`
                          : account.displayName}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          {result.results.map((item, index) => (
            <article
              key={`${item.account.id}-${item.check_name}-${index}`}
              className={`checks-result-row${
                backupSummary && item.check_name === "backup" && item.status !== "OK"
                  ? " arbel-backup-result-failed"
                  : ""
              }`}
            >
              <header>
                <h2>
                  {item.account.display_name} ({item.account.profile_name})
                </h2>
                <StatusBadge status={item.status} />
              </header>
              <p>{item.summary}</p>
              <CopyableOutput
                title={`${item.check_name} Output`}
                text={item.output || item.summary}
              />
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
