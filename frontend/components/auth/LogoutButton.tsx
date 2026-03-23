'use client'

import { Button } from '@/components/ui/button'
import { logoutAction } from '@/app/(dashboard)/logout/actions'

export function LogoutButton() {
  return (
    <form action={logoutAction}>
      <Button type="submit" variant="ghost">
        Sign out
      </Button>
    </form>
  )
}
