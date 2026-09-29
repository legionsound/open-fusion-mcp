-- Click OK on Resolve's render modals, and nothing else:
--   "Render completed!"                   (every comp.Render raises one)
--   "WARNING! Render did not complete!"   (a failed render)
-- Text is matched on each static text's name AND value (Resolve exposes it inconsistently).
-- Returns "<completed>|<failed>|<failure dialog text>;; ..."
on textsOf(w)
	set out to {}
	tell application "System Events"
		repeat with txtItem in (every static text of w)
			set vals to {}
			try
				set end of vals to name of txtItem
			end try
			try
				set end of vals to value of txtItem
			end try
			try
				set end of vals to description of txtItem
			end try
			repeat with v in vals
				try
					if contents of v is not missing value then
						set s to (contents of v) as text
						if s is not "" and out does not contain s then set end of out to s
					end if
				end try
			end repeat
		end repeat
	end tell
	return out
end textsOf

tell application "System Events"
	if not (exists process "Resolve") then return "0|0|"
	tell process "Resolve"
		set okN to 0
		set failN to 0
		set failText to ""
		repeat with w in (every window)
			try
				set isDone to (exists (static text "Render completed!" of w))
				set isFail to false
				set joined to ""
				repeat with s in (my textsOf(w))
					set s to s as text
					if s is "Render completed!" then set isDone to true
					if s contains "Render did not complete" then set isFail to true
					set joined to joined & s & " "
				end repeat
				if isFail then
					click button "OK" of w
					set failN to failN + 1
					set failText to failText & joined & ";; "
				else if isDone then
					click button "OK" of w
					set okN to okN + 1
				end if
			end try
		end repeat
		return (okN as text) & "|" & (failN as text) & "|" & failText
	end tell
end tell
