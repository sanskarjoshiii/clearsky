import { Link } from "react-router";

/** 404 shown inside a role app's own layout, so the navigation stays on screen. */
export function AppNotFound({ home }: { home: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      <p className="text-lg font-medium">Page not found</p>
      <Link to={home} className="text-sm text-muted underline">
        Go to your home page
      </Link>
    </div>
  );
}
