---
paths:
  - "**/*.{astro,html,jsx,svelte,tsx,vue}"
---
# Manual API Failure Checks

Applies when asking the user to reproduce an API failure by hand in Chrome.

Offer Chrome DevTools request blocking first: in the Network panel, right-click
the request and choose Block request. The request fails as a network error with
no HTTP status. Choose Throttle request instead to check a loading state.

Provide a console mock snippet only when a specific status code or response
body matters.
