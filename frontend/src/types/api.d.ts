/**
 * API type stubs — this file is overwritten by `npm run gen-types` (TASK-14).
 *
 * The script runs:
 *   openapi-typescript http://localhost:8000/openapi.json -o src/types/api.d.ts
 *
 * Until the backend is running and TASK-14 executes, these minimal stubs
 * keep TypeScript happy.
 */

export interface paths {
  "/auth/login": {
    post: {
      requestBody: {
        content: {
          "application/json": {
            email: string;
            password: string;
          };
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              access_token: string;
              token_type: string;
              user_id: string;
              email: string;
              default_format: string;
            };
          };
        };
        401: { content: { "application/json": { detail: string } } };
        403: { content: { "application/json": { detail: string } } };
      };
    };
  };
  "/auth/me": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              user_id: string;
              email: string;
              default_format: string;
              is_active: boolean;
              created_at: string;
              roles: Array<{
                role_id: string;
                role_name: string;
                role_type: string;
                domain: string | null;
              }>;
            };
          };
        };
      };
    };
  };
}

export type components = Record<string, never>;
export type operations = Record<string, never>;
