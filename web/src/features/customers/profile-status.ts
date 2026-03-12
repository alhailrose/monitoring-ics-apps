import type { Customer, ProfileStatus } from "../../types/api"

export type AuthType = "sso" | "iam" | "key" | null

export const pickExistingOrFirst = (rows: Customer[], currentId: string): string => {
  if (rows.some((customer) => customer.id === currentId)) {
    return currentId
  }
  return rows[0]?.id ?? ""
}

export const getAuthType = (profile: ProfileStatus | undefined): AuthType => {
  if (!profile) return null
  if (profile.sso_session) return "sso"
  if (profile.status === "ok") return "iam"
  if (profile.status === "error") return "key"
  return null
}

export const mapProfilesByName = (profiles: unknown): Record<string, ProfileStatus> => {
  if (!Array.isArray(profiles)) {
    return {}
  }

  const map: Record<string, ProfileStatus> = {}
  for (const profile of profiles) {
    if (typeof profile === "object" && profile !== null && "profile_name" in profile) {
      const typedProfile = profile as ProfileStatus
      map[typedProfile.profile_name] = typedProfile
    }
  }
  return map
}
