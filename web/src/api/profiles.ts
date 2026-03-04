import { apiRequest } from "./client"
import type { ProfileDetectionResponse } from "../types/api"

export function detectProfiles(): Promise<ProfileDetectionResponse> {
  return apiRequest<ProfileDetectionResponse>("/profiles/detect")
}
