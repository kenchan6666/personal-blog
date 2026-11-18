import { ViewTransition } from "react";

/**
 * Templates remount on every navigation, so the outgoing page exits and the
 * incoming page enters inside the router's transition. Browsers without the
 * View Transitions API simply swap the page.
 */
export default function LocaleTemplate({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ViewTransition enter="page-enter" exit="page-exit" default="none">
      {children}
    </ViewTransition>
  );
}
