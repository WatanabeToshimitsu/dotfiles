---
paths:
  - "**/*.{astro,css,dart,html,js,jsx,kt,scss,storyboard,svelte,swift,ts,tsx,vue,xib}"
  - "**/res/**/*.xml"
---
# UI

Applies when creating or changing a user interface.

Avoid unnecessary secondary labels and descriptions. Let the layout do the
explaining.

Keep text the user needs to act: form labels, accessible names such as
`aria-label` and alt text, input formats, constraints, and error messages.

## New interactions

When an interaction has no precedent in the codebase and its design is the
user's call, build two or three throwaway variants behind one switcher,
compare their screenshots, and bring them with the recommendation.
