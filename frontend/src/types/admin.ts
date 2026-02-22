/**
 * Admin-specific TypeScript types derived from the FastAPI Pydantic schemas.
 *
 * Source of truth:
 *   policy_system/api/schemas.py
 *   policy_system/api/routers/admin.py
 */

export interface RoleResponse {
  role_id: string;
  role_name: string;
  role_type: string;
  domain: string | null;
}

export interface UserResponse {
  user_id: string;
  email: string;
  default_format: string;
  is_active: boolean;
  created_at: string;
  roles: RoleResponse[];
}

export interface DocumentResponse {
  doc_id: string;
  title: string;
  storage_uri: string;
  is_archived: boolean;
  uploaded_by: string | null;
  created_at: string;
  roles: RoleResponse[];
}

export interface UserCreatePayload {
  email: string;
  password: string;
  default_format?: string;
}

export interface DocumentCreatePayload {
  title: string;
  storage_uri: string;
  role_ids: string[];
}

export interface DocumentArchiveTogglePayload {
  is_archived: boolean;
}

export interface RoleAssignPayload {
  role_id: string;
}

export interface MessageResponse {
  message: string;
}
