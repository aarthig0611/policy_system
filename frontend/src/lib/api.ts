/**
 * openapi-fetch client pointing to the Next.js proxy (/api/backend → FastAPI :8000).
 *
 * Types will be filled in during TASK-14 once `npm run gen-types` is run.
 * Until then we use `any` as a placeholder so the rest of the app can import
 * this module without TypeScript errors.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
import createClient from "openapi-fetch";

// Minimal stub — replaced by the generated `api.d.ts` in TASK-14
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ApiPaths = Record<string, any>;

const client = createClient<ApiPaths>({
  baseUrl: "/api/backend",
});

export { client };
export type { ApiPaths };
