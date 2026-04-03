import 'server-only'

type OAuthStatePayload = {
  csrf: string
  inviteToken?: string
}

export function encodeOAuthState(payload: OAuthStatePayload): string {
  return Buffer.from(JSON.stringify(payload), 'utf-8').toString('base64url')
}

export function decodeOAuthState(state: string): OAuthStatePayload | null {
  try {
    const parsed = JSON.parse(Buffer.from(state, 'base64url').toString('utf-8')) as {
      csrf?: unknown
      inviteToken?: unknown
    }
    if (typeof parsed.csrf !== 'string' || parsed.csrf.length === 0) {
      return null
    }
    return {
      csrf: parsed.csrf,
      inviteToken: typeof parsed.inviteToken === 'string' ? parsed.inviteToken : undefined,
    }
  } catch {
    return null
  }
}

export function getGoogleAuthUrl(state: string): string {
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
