import { decodeOAuthState, encodeOAuthState } from '@/lib/google-oauth'

describe('google oauth state helpers', () => {
  it('roundtrips csrf + invite token through state payload', () => {
    const state = encodeOAuthState({ csrf: 'csrf-123', inviteToken: 'invite-abc' })
    const parsed = decodeOAuthState(state)

    expect(parsed).toEqual({ csrf: 'csrf-123', inviteToken: 'invite-abc' })
  })

  it('returns null for invalid state payload', () => {
    expect(decodeOAuthState('not-a-valid-state')).toBeNull()
  })
})
