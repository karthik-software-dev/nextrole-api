export interface UserProfile {
  id: number;
  name: string;
  email: string;
  target_role: string;
}

export interface SearchScoring {
  min_experience: number;
  max_experience: number;
  min_score: number;
  target_locations: string[];
}

export interface IntegrationsSettings {
  apify_api_token: string | null;
  is_apify_configured: boolean;
}

export interface ApifyTestResult {
  valid: boolean;
  username?: string | null;
  message: string;
}

export interface SettingsData {
  profile: UserProfile;
  scoring: SearchScoring;
  integrations?: IntegrationsSettings;
}

export interface UpdateSettingsPayload {
  profile?: {
    name?: string;
    email?: string;
    target_role?: string;
  };
  scoring?: {
    min_experience?: number;
    max_experience?: number;
    min_score?: number;
    target_locations?: string[];
  };
  integrations?: {
    apify_api_token?: string | null;
  };
}

export interface FeedViewSettings {
  defaultTier: string;
  defaultSort: string;
  defaultPageSize: number;
}
