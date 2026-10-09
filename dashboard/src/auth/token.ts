import { env } from "../env";

/**
 * Token storage for the two auth modes.
 * - dev: an unsigned "dev.<role>.<id>" token from the local dev server (DEV_AUTH only).
 * - cognito: the Cognito ID token from Amplify (refreshed by Amplify).
 */
const DEV_KEY = "clearsky.devToken";
let unauthorizedHandler: (() => void) | null = null;

export function setDevToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(DEV_KEY, token);
    else localStorage.removeItem(DEV_KEY);
  } catch {
    /* storage blocked: the session just won't persist */
  }
}

function readDevToken(): string | null {
  try {
    return localStorage.getItem(DEV_KEY);
  } catch {
    return null;
  }
}

/**
 * `forceRefresh` asks Cognito for a new ID token. Needed right after the officer approves a
 * registration: the group and baler/buyer id are only in a freshly issued token.
 */
export async function getToken(forceRefresh = false): Promise<string | null> {
  if (env.authMode === "dev") return readDevToken();
  const { fetchAuthSession } = await import("aws-amplify/auth");
  try {
    const session = await fetchAuthSession({ forceRefresh });
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

export function onUnauthorized(): void {
  unauthorizedHandler?.();
}

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  unauthorizedHandler = fn;
}
