import type { Account, Customer } from "../../types/api"

export type ArbelMenu = "backup" | "rds" | "ec2" | "alarm" | "budget"

export type MenuConfig = {
  key: ArbelMenu
  label: string
  description: string
  checkName: string
}

export const MENUS: MenuConfig[] = [
  {
    key: "backup",
    label: "Backup Status",
    description: "Check AWS Backup job status across accounts",
    checkName: "backup",
  },
  {
    key: "rds",
    label: "RDS Metrics",
    description: "Daily RDS metric monitoring with threshold alerts",
    checkName: "daily-arbel",
  },
  {
    key: "ec2",
    label: "EC2 Metrics",
    description: "Daily EC2 metric monitoring with threshold alerts",
    checkName: "daily-arbel",
  },
  {
    key: "alarm",
    label: "Alarm Verification",
    description: "Verify CloudWatch alarm states and breach history",
    checkName: "alarm_verification",
  },
  {
    key: "budget",
    label: "Daily Budget",
    description: "Check AWS Budgets threshold and over-budget alerts",
    checkName: "daily-budget",
  },
]

export const WINDOW_OPTIONS = [
  { value: 1, label: "1 jam" },
  { value: 3, label: "3 jam" },
  { value: 12, label: "12 jam" },
]

export const getAlarmNames = (account: Account): string[] => {
  if (account.alarm_names && account.alarm_names.length > 0) {
    return account.alarm_names
  }

  const extra = account.config_extra as Record<string, unknown> | null
  if (!extra) return []
  const av = extra.alarm_verification as Record<string, unknown> | undefined
  if (!av) return []
  const names = av.alarm_names
  return Array.isArray(names) ? (names as string[]) : []
}

export const hasAlarms = (account: Account): boolean => getAlarmNames(account).length > 0

export const pickArbelCustomer = (rows: Customer[]): Customer | null => {
  return (
    rows.find((customer) => customer.name.toLowerCase() === "aryanoble") ||
    rows.find((customer) => customer.display_name.toLowerCase().includes("aryanoble")) ||
    null
  )
}

export const getDefaultConsolidatedOutput = (outputs: Record<string, string>): string => {
  const firstKey = Object.keys(outputs)[0]
  return firstKey ? outputs[firstKey] : ""
}
