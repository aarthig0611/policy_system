/**
 * Auth layout — wraps login (and any future register/forgot-password) pages.
 * No sidebar or navbar — just a clean centered shell.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
