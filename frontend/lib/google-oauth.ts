import 'server-only'

export function getGoogleAuthUrl(state: string, inviteToken?: string): string {
  const redirectUri = process.env.GOOGLE_REDIRECT_URI!
  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID!,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
    hd: 'icscompute.com',
    state,
    access_type: 'online',
    prompt: 'select_account',
  })
  if (inviteToken) params.set('invite_token', inviteToken)
  return `https://accounts.google.com/o/oauth2/v2/auth?${params}`
}

export async function exchangeCodeForIdToken(code: string): Promise<string> {
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID!,
      client_secret: process.env.GOOGLE_CLIENT_SECRET!,
      redirect_uri: process.env.GOOGLE_REDIRECT_URI!,
      grant_type: 'authorization_code',
    }),
  })
  if (!res.ok) throw new Error('Failed to exchange code for token')
  const data = await res.json()
  return data.id_token as string
}
