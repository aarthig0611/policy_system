import { redirect } from "next/navigation";

/**
 * Root page — immediately redirect to /chat.
 *
 * If the user is not authenticated the middleware will intercept the /chat
 * request and redirect them to /login instead.
 */
export default function RootPage() {
  redirect("/chat");
}
