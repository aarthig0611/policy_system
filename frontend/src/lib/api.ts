/**
 * openapi-fetch client pointing to the Next.js proxy (/api/backend → FastAPI :8000).
 *
 * Typed against the generated `src/types/api.d.ts` (produced by `npm run gen-types`).
 * The `paths` export from that file describes every endpoint, request body, and
 * response shape — openapi-fetch uses it to infer argument and return types at
 * compile time.
 */

import createClient from "openapi-fetch";
import type { paths } from "@/types/api";

const client = createClient<paths>({
  baseUrl: "/api/backend",
});

export { client };
export type { paths as ApiPaths };
