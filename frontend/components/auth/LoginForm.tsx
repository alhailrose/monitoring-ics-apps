'use client'

import { useActionState } from 'react'
import { useFormStatus } from 'react-dom'
import { loginAction } from '@/app/(auth)/login/actions'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <Button type="submit" className="w-full" disabled={pending}>
      {pending && <Spinner className="mr-2" />}
      Login
    </Button>
  )
}

export function LoginForm() {
  const [state, action] = useActionState(loginAction, null)

  return (
    <Card className="border-border/60 shadow-2xl shadow-black/5">
      <CardHeader>
        <CardTitle className="text-xl">Sign in to ICS Monitoring</CardTitle>
        <CardDescription>
          Masuk ke ruang kendali ICS menggunakan kredensial internal dengan sesi MFA yang diaudit.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={action} className="flex flex-col gap-4">
          {state?.error && (
            <Alert variant="destructive">
              <AlertDescription>{state.error}</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-col gap-2">
            <label htmlFor="username" className="text-sm font-medium">
              Username
            </label>
            <Input id="username" name="username" type="text" required autoComplete="username" />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="password" className="text-sm font-medium">
              Password
            </label>
            <Input id="password" name="password" type="password" required autoComplete="current-password" />
          </div>
          <SubmitButton />
        </form>
        <p className="mt-4 text-[11px] text-muted-foreground">
          Akses terbatas untuk personel ICS. Aktivitas login dipantau otomatis.
        </p>
      </CardContent>
    </Card>
  )
}
