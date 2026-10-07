# React Server and Hydration Boundaries

- Detect actual framework/rendering support first. Ordinary React/Vite does not imply Next.js or React Server Components. Respect installed framework versions and server/client module boundaries.
- Keep credentials, database access and privileged operations on the server. Validate client-supplied action/route inputs, reuse current authentication/authorization rather than assuming framework transport grants access.
- Preserve serializable props where required and request-specific state isolation. Browser globals/listeners belong in client lifecycle, not server execution.
- Hydration requires equivalent initial output. Inspect time/random/locale/browser storage and IDs before suppressing warnings. Confirm how suspense, streaming and error boundaries behave in the configured runtime.
- Static/client deployments cannot silently depend on server routes/actions. Preserve router/assets base and explicit unavailable/error states.
- Check the changed server response, client hydration/console, navigation, auth/error states and target deployment mode with actual project tools. Do not upgrade frameworks or turn the task into an unsolicited architecture migration.

Sources: [hydrateRoot](https://react.dev/reference/react-dom/client/hydrateRoot), [Server Components](https://react.dev/reference/rsc/server-components).
