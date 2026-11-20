---
paths:
  - "**/*.{astro,css,dart,html,js,jsx,kt,scss,storyboard,svelte,swift,ts,tsx,vue,xib}"
  - "**/res/**/*.xml"
---
# UI

Applies when creating or changing a user interface.

For a change meant to keep the look, capture baseline screenshots of the
affected states before editing and compare by image diff. Never edit the
baseline to make a diff pass.

Avoid unnecessary secondary labels and descriptions. Let the layout do the
explaining.

Keep text the user needs to act: form labels, accessible names such as
`aria-label` and alt text, input formats, constraints, and error messages.

## New interactions

When an interaction has no precedent in the codebase and its design is the
user's call, build two or three throwaway variants behind one switcher,
compare their screenshots, and bring them with the recommendation.
