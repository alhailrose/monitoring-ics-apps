import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const WIB = { timeZone: 'Asia/Jakarta' } as const

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    ...WIB,
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    ...WIB,
    day: '2-digit',
    month: 'short',
  })
}

export function formatDateFull(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    ...WIB,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
