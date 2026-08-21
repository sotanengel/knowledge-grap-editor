/** A failure the user can read, rather than a console message they cannot. */
export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="rounded-md bg-red-100 px-3 py-2 text-xs text-red-900 dark:bg-red-900/40 dark:text-red-100"
    >
      {message}
    </p>
  );
}
