import { render, screen } from '@testing-library/react'
import LoginPage from '@/app/(auth)/login/page'

jest.mock('@/lib/auth', () => ({ getSession: jest.fn().mockResolvedValue(null) }))
jest.mock('next/navigation', () => ({
  redirect: jest.fn(),
  useSearchParams: () => new URLSearchParams(),
}))

it('includes hero footer credit', async () => {
  render(await LoginPage({ searchParams: Promise.resolve({}) }))
  expect(screen.getByText(/Made by Bagus Ganteng 😎/i)).toBeInTheDocument()
})
