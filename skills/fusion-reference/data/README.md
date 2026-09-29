# fusion-reference/data (generated on your machine, not shipped)

The connector and the skills read three files from this folder. They describe Blackmagic's software (every
tool's registry ID, input IDs, labels, defaults, ranges and option lists, plus API stubs), so this repository
ships the way to make them, not the files. Generate them once after installing DaVinci Resolve Studio 21.1, and
again after a Resolve update.

| file | what it is | how to get it |
|---|---|---|
| `fusion-21.1-registry.tsv` | one row per registry entry: `reg_id, name, category, class, kind` | harvest from your running Resolve (below) |
| `fusion-21.1-inputs.tsv` | a `@RegID` header line per tool, then one row per input: `tool, input_id, ui_name, type, control, default, slider_range\|allowed_range, options, page` | harvest from your running Resolve (below) |
| `fusion_api-21.1.pyi` | Python type stubs for the Fusion and Resolve scripting objects | the official DaVinci Resolve MCP's `get_scripting_api` tool; Resolve also ships `Developer/Scripting/DaVinciResolveScript.pyi` for the Resolve half |

## Harvest

Work in a scratch project (the examples use one called `Testbed`) with an empty Fusion comp on the Fusion page.

- **Inputs:** `../../fusion-motion-design/scripts/harvest_inputs.py` adds each tool, reads every input's
  `GetAttrs()` (ID, name, data type, control, default, ranges, option lists, page) and the output IDs, then
  deletes the tool. Run it through the official Resolve MCP (`run_script_unsafe`) in batches of 60 to 100 tools
  per call; its docstring has the calls. Some inputs exist only in a mode (Renderer3D OpenGL settings, Text+
  shading elements 2 to 8): pass `modes`.
- **Registry:** one row per entry of `fusion:GetRegList()`, from each entry's attributes (ID, name, category,
  class type), with `kind` set to tool, modifier or other.
- **Writing the TSVs** from the harvest JSON follows the column lists above; the first two comment lines of
  each file record the Resolve version and what was left out (Settings-tab inputs common to every tool, color
  gamut tags, frame-format inputs).

Not scripted yet: the registry step and the JSON-to-TSV writer (a `fusion-connector harvest` command is the
planned home for both).

Without these files the connector still starts: `fusion-connector doctor` reports the tables as missing, the
server skips its offline ID checks, and features that need defaults (graph layout, pasted-default drift checks)
are degraded. 15 of the 142 offline tests need the tables and fail without them.
