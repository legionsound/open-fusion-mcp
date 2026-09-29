# 18 Adopting a handoff from another pipeline

Load when a handoff, spec, `HANDOFF.md`, build notes, or a `.comp`/`.setting` file arrives from
another machine, agent or pipeline (including an After Effects build of the same brief). Port of
Higgsfield `ae-clean-rig` module 18 (local connector, 2026-09-26).

A handoff is one document holding two kinds of content. Separate them before building.

- **Findings** are what the other machine observed: installed and licensed plugins, available fonts,
  failures that reproduced, timings and values that worked, and which words in the reference led to
  which motion idea. Take these on board: they are usually correct and expensive to find again.
- **Techniques** are how that pipeline solved the problem. They do not transfer by default. A pipeline
  with unrestricted scripting can hide animation in expressions, overwrite text with generated strings
  and drive everything from `time`, because it never had to hand an editable project to a person.
  Check each technique against this skill; where they disagree the skill wins, and the handoff's
  on-screen result is still the target to match.

The failure mode is reading the handoff as an architecture recipe. A build that inherits its structure
wholesale can look identical and be far worse to hand over: fewer named groups, motion buried in
expressions, text no longer editable, controls that do nothing.

## Findings worth carrying

- **Probe plugin licenses before designing around them.** Apply each OFX or Fuse the handoff relies on
  to a scratch Fusion comp in a scratch project, render one frame with a Saver and look for a
  watermark; an unlicensed plugin does not fail, it silently marks the render. Also confirm the Resolve
  edition (Studio-only Resolve FX) and version on this machine (15 dependency audit).
  [verified live 2026-09-26, mechanics only] In a lab comp on Studio 21.1, `tool.add` of
  `ofx.com.blackmagicdesign.resolvefx.GaussianBlur` (image input `Source`) and `Fuse.Duplicate`
  (image input `Background`), each fed a counter plate and rendered through a temporary Saver PNG,
  rendered clean with no watermark and no dialog (`t18_ofx_gaussian_f5.png`,
  `t18_fuse_duplicate_f5.png`). No third-party OFX was probed (a license prompt could open a modal);
  what an unlicensed plugin's mark looks like here is unverified.
- **A second aspect ratio is a new layout**, not a crop; check component widths before promising one
  (components authored at full frame width need resizing, not only rearranging; Text+ `Size` and
  sShapes are width-relative, 06).
- Keep a **defect seen in frame -> cause -> fix** table in the report. It is reviewable and separates a
  reproduced failure from a suspected one.
- When the reference is a still, its own wording can drive motion ideas (a word in the artwork
  legitimately earns a beat); an invented flicker cannot.

## Techniques to check rather than copy

- A handoff that reached Resolve by a route this setup does not use (external FuScript sessions,
  Fusion Studio standalone, UI automation, `run_script_unsafe` file tricks) describes a control path,
  not a requirement. Build the same result through this skill's routes (Resolve API, `.setting` paste,
  fusion_kit) and report a real gap only where one exists.
- A workaround may not be a constraint here. Rules like "never rotate a Text+" or "never address a
  tool by index" often record one pipeline's crashes: verify on this path before inheriting them, and
  drop those that do not reproduce. The facts in [fusion-realities](../../fusion-reference/references/fusion-realities.md)
  are the verified list for this machine.
- A `.comp`/`.setting` from elsewhere: check Loader `Clip` paths (absolute paths from the other
  machine), fonts, Fuse/OFX RegIDs, the Resolve/Fusion version it came from, frame format, and
  expressions that replace keys with `time` math. Paste into a scratch comp first (unique prefix,
  realities §9), render, then decide what to rebuild as controllers and sparse keys (06, 02).
- Never adopt a step that closes or overwrites the user's open project. Back up first (comp export,
  `.drp`), then work in a scratch project or a named iteration.

## What to state

Say which parts of the handoff you took on as findings, which techniques you turned down and why, and
which of its claims you could not check here. A handoff is evidence produced somewhere else; it proves
nothing about this machine until you have reproduced it.
