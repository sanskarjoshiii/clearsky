/** Build-time configuration (Vite env). See dashboard/README.md for every variable. */
export const env = {
  apiUrl: (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "",
  authMode: ((import.meta.env.VITE_AUTH_MODE as string | undefined) ?? "dev") as "dev" | "cognito",
  region: (import.meta.env.VITE_AWS_REGION as string | undefined) ?? "ap-south-1",
  userPoolId: (import.meta.env.VITE_USER_POOL_ID as string | undefined) ?? "",
  userPoolClientId: (import.meta.env.VITE_USER_POOL_CLIENT_ID as string | undefined) ?? "",
  mapStyleUrl: (import.meta.env.VITE_MAP_STYLE_URL as string | undefined) ?? "",
};
