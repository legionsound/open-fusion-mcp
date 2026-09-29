# Collage: editable prompt interface

Only when a prompt-driven demo or chat-style composer is requested. Recipes are
**status: unverified (not yet rendered)**.

- Rebuild the interface natively (ui-mastery): surface, optional header, prompt Text+, caret, controls,
  restrained shadow. The composer is animated artwork unless a real input connection is separately
  built; an access label, model name or microphone icon proves nothing about live function.
- Stable layout matching the reference's spacing and hierarchy; wording and labels are runtime inputs.
  Build the UI as its own group merged **after** the collage finishing (grain, boil, cadence) so paper
  distortion never touches it (overview step 8).
- Size type in final output pixels (`Size ~= 1.70 x font_px / W`, realities §2), accounting for any
  group scale. Keep input text clear of the control row and let a longer command fit without hitting an
  icon (06 longer-label test). When swapping the interface source, refit its `Pivot` and size for the new
  dimensions and keep the approved placement and timing.
- Merge order is explicit: surface first (Background of the UI Merge), then text and icons as
  Foregrounds. Controls from `sRectangle`/`sEllipse`/`sPolygon` or masked Backgrounds; strokes via
  `BorderWidth`/`sOutline`.
- Full command text lives in `StyledText`; the typing is a Write On (`End`) on it. Typing interval and
  visible lifetime are different: the completed text stays readable until its next state.
- Caret: a thin `sRectangle` whose `Translate.X` follows the revealed text's right edge
  (`Prompt.Output[0].DataWindow[3]/Prompt.Output[0].Width` gives it in 0..1 of the image; sShape units
  are width fractions from center, so subtract 0.5), hidden when the bar is hidden, never visible before
  its text tool, blinking in idle states: `Blend = iif(CTRL_UI.Typing > 0.5, 1, iif(math.floor(time/12) % 2 == 0, 1, 0))`
  (1 s blink at 24 fps). [verified live 2026-09-26] `DataWindow` tracks a partial Write On: the
  expression `Prompt.Output[0].DataWindow[3]/Prompt.Output[0].Width - 0.5` put the caret at the
  revealed text's right edge within 1 px at 25 %, 50 % and 100 % (left-justified Text+). With nothing
  revealed yet it returned garbage (-260.9): guard with `iif(Prompt.End <= 0, <start x>, ...)` or hide
  the caret until the first character.
- Causality: the command becomes readable, an explicit submit or response state happens when asked for,
  then the matching background change, object swap or added animation follows. A decorative voice
  button is not a submit animation. Never claim a prompt action was implemented unless its visual
  result is present and correctly timed.
