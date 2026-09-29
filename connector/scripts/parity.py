"""Generate PARITY.md: every AE connector operation (study/ae_ops.json, 197 ops) -> Fusion operation,
different model, or n/a; plus the tool-level mirror, the lordhoell/davinci-resolve-mcp comparison
column, and live smoke results (tests/smoke_results.json)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

I, D, N = "implemented", "different model", "n/a"

# AE op -> (status, fusion op(s) or "", note)
MAP = {
    # batch / command
    "batch.run": (I, "batch.run", "one call, one undo event (StartUndo/EndUndo on the batch comp), children validated like top-level calls, no automatic rollback"),
    "command.execute": (I, "command.execute", "Fusion actions (comp:DoAction) instead of AE menu command IDs"),
    "command.find": (I, "command.find", "searches Fusion ActionManager actions"),
    "command.list": (I, "command.list", ""),
    # comp
    "comp.create": (D, "comp.create, timeline.create, timeline.add_fusion_clip", "a Fusion comp lives on a timeline clip: new Fusion Composition clip, AddFusionComp on an item (any track), or an exact-length Fusion item on any track (black carrier)"),
    "comp.set_label": (D, "tool.set_attrs (tileColor)", "comps have no label color; node tile colors are the Fusion equivalent"),
    "comp.set_props": (D, "comp.set_format, comp.set_render_range, pref.set, timeline.set_format", "comp properties are prefs (Comp.FrameFormat...) and attrs; the timeline format sets a Fusion clip's size and rate; bg color = a Background tool"),
    "comp.set_renderer": (D, "3d.add_renderer (rendererType)", "3D rendering is a Renderer3D node (Software/OpenGL/OpenGLUV), not a comp setting"),
    "comp.list_renderers": (D, "effect.inputs {regId: Renderer3D}", "RendererType options come from the live TSV"),
    "comp.set_work_area": (I, "comp.set_render_range", "render range = work area; global range follows the clip length"),
    "comp.add_guide": (N, "", "Fusion viewer guides are not scriptable through the Resolve API"),
    "comp.remove_guide": (N, "", "as comp.add_guide"),
    "comp.set_guide": (N, "", "as comp.add_guide"),
    "comp.list_guides": (N, "", "as comp.add_guide"),
    "comp.delete": (I, "comp.delete, timeline.delete", "delete a comp from an item (or the scratch timeline)"),
    "comp.precompose": (D, "template.write_macro, setting.copy + setting.paste", "no precomp: group/macro the tools, or build in a second comp"),
    "comp.duplicate": (D, "comp.export_file + comp.import_file, setting.copy + setting.paste", "copy the graph as .comp/.setting"),
    "comp.info": (I, "comp.info / fu_comp_info", ""),
    # effect
    "effect.add": (I, "effect.add", "inserts the filter after a tool and reroutes its consumers (the node equivalent of an effect on a layer)"),
    "effect.remove": (I, "effect.remove", "heals the pipe"),
    "effect.list_on_layer": (I, "effect.chain", "upstream main-input chain"),
    "effect.set_property": (I, "input.set / input.set_many", "effects are tools; their controls are inputs"),
    "effect.move": (D, "input.connect", "reorder by rewiring the chain"),
    "effect.set_dropdown_items": (I, "input.add_control (type combo, options)", "user-control combo on any tool"),
    "effect.get_dropdown_items": (I, "input.list", "combo options come back in the input attrs / TSV"),
    # egp (Essential Graphics / MOGRT)
    "egp.set_name": (D, "template.write_macro (macro)", "the macro name is the template name"),
    "egp.add_property": (D, "template.write_macro (publish), input.publish", "published macro inputs = Essential Graphics controllers"),
    "egp.list_controllers": (D, "setting.validate on the macro / tool.info on the macro", "published inputs are the macro's inputs"),
    "egp.export_mogrt": (D, "template.write_macro + template.install", ".setting macro installed as an Edit-page Title/Effect/Transition/Generator"),
    "egp.set_alternate_source": (N, "", "media replacement controllers are an EGP/Premiere concept"),
    "egp.add_layer": (D, "template.write_macro (mainInputs)", "expose an image input as MainInput"),
    "egp.open_in_panel": (N, "", "no Essential Graphics panel in Fusion"),
    # expression
    "expression.set": (I, "expression.set", "SimpleExpressions; verified evaluation, nil reverts; noise() refused"),
    "expression.disable_all": (I, "expression.disable_all", "value-restoring clear with a manifest"),
    "expression.restore_all": (I, "expression.restore_all", "with replacements"),
    "expression.remove": (I, "expression.clear", "SetExpression(None) + value restore (live: '' breaks the input)"),
    # font
    "font.list": (I, "font.list", "Fusion FontManager"),
    "font.list_missing": (I, "font.list_used (missing)", ""),
    "font.info": (I, "font.info", "styles and files"),
    "font.check_glyphs": (N, "", "no glyph-coverage API in Fusion; render and inspect (render.frame)"),
    "font.list_used": (I, "font.list_used", ""),
    "font.list_duplicates": (N, "", "FontManager exposes family/style -> file only"),
    "font.get_lists": (N, "", "no favorites/MRU font lists in Fusion scripting"),
    "font.set_favorites": (N, "", "as font.get_lists"),
    "font.set_substitution": (N, "", "no font substitution policy API"),
    "font.get_default_for_script": (N, "", "no per-script default font API"),
    "font.set_default_for_script": (N, "", "as above"),
    # footage
    "footage.replace": (I, "media.replace", "Loader Clip or MediaIn media ID"),
    "footage.interpret": (D, "input.set on Loader/MediaIn (PixelAspect, Loop, Hold*, MakeAlphaSolid, PostMultiplyByAlpha ...)", "interpretation lives on the Loader/MediaIn tool"),
    "footage.reload": (D, "media.replace (same path)", "re-set Clip to force a reload"),
    "footage.list_missing": (I, "media.list (missing)", ""),
    "footage.replace_with_solid": (D, "tool.add Background + input.connect", "a Background tool is the solid"),
    "footage.replace_with_placeholder": (D, "tool.add Background", "same"),
    "footage.set_proxy": (N, "", "proxies are Resolve media/render cache settings, not per-tool scripting"),
    # item (project panel) -> Media Pool
    "folder.create": (I, "item.create_folder", "Media Pool folder"),
    "item.move_to_folder": (N, "", "not exposed here; Media Pool moves are outside Fusion scope (official Resolve MCP covers it)"),
    "item.set_props": (N, "", "Media Pool clip metadata is an Edit/Media-page concern (official Resolve MCP)"),
    "item.list": (I, "item.list", "Media Pool clips with media IDs"),
    "item.usages": (I, "item.usages", "timelines using a clip"),
    # keyframe
    "keyframe.add": (I, "keyframe.add", "Number via BezierSpline, Point via XYPath; merge; stray-key fix; asserted key set"),
    "keyframe.remove": (I, "keyframe.remove", "by frame"),
    "keyframe.set_easing": (I, "keyframe.set_easing", "cubic-bezier presets, [x1,y1,x2,y2], or AE influence/speed"),
    "keyframe.set_batch": (I, "keyframe.add (keys array)", ""),
    "keyframe.shift": (I, "keyframe.shift", "offset/scale/pivot"),
    "keyframe.copy": (I, "keyframe.copy", "with eases and time offset"),
    "keyframe.set_spatial": (D, "keyframe.add on Point (XYPath) / modifier.add PolyPath", "Fusion paths: XYPath (per-axis splines) or PolyPath (spatial Bezier path); no per-key spatial tangents API"),
    "keyframe.set_roving": (N, "", "no roving keys in Fusion"),
    "keyframe.set_value": (I, "keyframe.set_value", "eases preserved"),
    "keyframe.set_interpolation": (I, "keyframe.set_easing (linear | hold | bezier)", "hold = StepIn flags"),
    "keyframe.set_label": (N, "", "no key labels"),
    "keyframe.set_selected": (N, "", "spline editor selection is UI state"),
    # layer -> tool
    "layer.create_solid": (I, "tool.add Background / input.set_color", ""),
    "layer.create_shape": (I, "shape.add", "sShapes"),
    "layer.create_text": (I, "tool.add TextPlus / text.set_style", ""),
    "layer.create_null": (D, "tool.add PipeRouter / Transform", "no nulls; a Transform or a Custom/PipeRouter controller node"),
    "layer.create_camera": (I, "3d.add_camera", "explicit film back"),
    "layer.create_light": (I, "3d.add_light", ""),
    "layer.create_parametric_mesh": (I, "3d.add_shape", "Shape3D plane/cube/sphere/cylinder/cone/torus, Text3D"),
    "layer.delete": (I, "tool.delete", "glob patterns, orphan modifiers removed"),
    "layer.duplicate": (I, "tool.duplicate", ""),
    "layer.set_parent": (D, "input.link / expression.set", "no parenting: link inputs or stack Transforms"),
    "layer.scene_edit_detection": (N, "", "an Edit/Media-page feature (official Resolve MCP)"),
    "layer.move": (D, "input.connect / merge.stack", "stacking order = Merge chain order"),
    "layer.create_footage": (I, "media.add_mediain, media.add_loader", ""),
    "layer.set_enabled": (I, "tool.set_attrs (passThrough)", ""),
    "layer.set_guide": (D, "tool.set_attrs (passThrough)", "no guide layers; pass-through keeps a reference node out of the render"),
    "layer.set_props": (I, "tool.set_attrs, input.set_many", ""),
    "layer.add_guide": (N, "", "layer-panel guides do not exist in Fusion"),
    "layer.remove_guide": (N, "", "as above"),
    "layer.move_guide": (N, "", "as above"),
    "layer.list_guides": (N, "", "as above"),
    "layer.bounds": (I, "tool.bounds", "DoD (cheap) or rendered alpha bbox (exact)"),
    "layer.convert_point": (D, "units are explicit: {px:[x,y]} inputs and *Px params", "normalized Y-up vs pixels is converted by every op"),
    "layer.apply_preset": (I, "setting.paste", ".setting presets"),
    "layer.replace_source": (I, "media.replace, input.connect", ""),
    "layer.set_track_matte": (I, "merge.set_matte", "EffectMask + channel + invert"),
    "layer.set_blend_mode": (I, "merge.set_blend_mode", "Merge ApplyMode"),
    "layer.split": (N, "", "trimming clips is an Edit-page operation (official Resolve MCP)"),
    "layer.copy_to_comp": (I, "setting.copy + setting.paste", ""),
    "layer.calculate_transform": (N, "", "no corner-pin solver API; CornerPositioner/Perspective tools are set manually"),
    "layer.info": (I, "tool.info / fu_tool_info", ""),
    # marker
    "marker.add_comp": (I, "marker.add (on: item)", "clip markers; comp.SetMarker ignores time (live)"),
    "marker.add_layer": (D, "marker.add (on: item | timeline)", "tools carry no markers"),
    "marker.remove": (I, "marker.remove", ""),
    "marker.update": (I, "marker.update", ""),
    "marker.list": (I, "marker.list", ""),
    # mask
    "mask.add": (I, "mask.add, mask.add_polygon", "measured units"),
    "mask.set_path": (I, "mask.add_polygon", "Polyline via .setting paste (the bridge cannot write Polyline values)"),
    "mask.set_props": (I, "mask.set_props", "softness/expansion in px"),
    "mask.remove": (I, "tool.delete / merge.set_matte (no matte)", ""),
    # pref
    "pref.get": (I, "pref.get", "comp or app scope"),
    "pref.set": (I, "pref.set", "app scope needs confirm"),
    "pref.delete": (N, "", "not exposed (DeletePrefs is destructive to app config)"),
    "pref.get_setting": (I, "data.get", "comp/tool SetData store"),
    "pref.set_setting": (I, "data.set", ""),
    # project
    "project.open": (I, "project.load", "allowlisted projects only (confirm without an allowlist); after a Resolve restart Resolve can land on 'Untitled Project'"),
    "project.import_file": (I, "item.import", "Media Pool import"),
    "project.undo": (I, "comp.undo, comp.redo", "runs outside the undo group; not batchable"),
    "project.purge": (N, "", "cache purge is a Resolve playback setting"),
    "project.replace_font": (I, "font.replace", ""),
    "project.auto_fix_expressions": (I, "expression.replace_text", ""),
    "project.clear": (N, "", "deliberately not offered (destructive)"),
    "project.delete_item": (I, "item.delete", "confirm required"),
    "project.find_layers": (I, "tool.list (regId, name glob, kind)", ""),
    "project.list_effects": (I, "effect.list_available, effect.inputs", "offline from the live registry"),
    "project.set_settings": (D, "comp.set_format, pref.set", "project settings are Resolve's; comp prefs cover Fusion"),
    "project.get_settings": (D, "project.info, comp.format, pref.get", ""),
    "project.reduce": (N, "", "no Fusion equivalent"),
    "project.remove_unused_footage": (N, "", "Media Pool housekeeping (official Resolve MCP)"),
    "project.consolidate_footage": (N, "", "as above"),
    "project.import_placeholder": (D, "tool.add Background", "a Background stands in"),
    "project.new": (N, "", "never creates/switches projects"),
    "project.parse_swatch": (N, "", "no swatch parser; colors are hex/rgb everywhere"),
    "project.get_xmp": (N, "", "no XMP on comps"),
    "project.set_xmp": (N, "", "no XMP on comps"),
    "project.set_default_import_folder": (N, "", "no equivalent"),
    "project.get_tool": (D, "tool.select (active tool)", "no toolbar tool; the active node is the analog"),
    "project.set_tool": (D, "tool.select", ""),
    "project.set_memory_limits": (D, "system.memory", "Resolve memory prefs are app configuration outside scripting; system.memory reports the footprint with a restart warning instead"),
    "project.set_multi_frame_rendering": (N, "", "no MFR switch"),
    # property -> input
    "property.set": (I, "input.set", "validated + read back"),
    "property.get": (I, "input.get", "fractional frames"),
    "property.list": (I, "input.list", ""),
    "property.add": (I, "input.add_control, modifier.add", "user controls / modifiers"),
    "property.remove": (I, "modifier.remove, tool.delete", ""),
    "property.separate_dimensions": (I, "keyframe.add on a Point input (XYPath)", "XYPath = separated X/Y"),
    "property.move": (N, "", "input order is fixed"),
    "property.select": (N, "", "Inspector selection is UI state"),
    # render
    "render.add_to_queue": (I, "deliver.add_job", "Deliver page queue"),
    "render.start": (I, "deliver.start", ""),
    "render.clear_queue": (D, "deliver.remove_job (per job)", "only jobs the caller created are removed"),
    "render.set_output": (I, "deliver.add_job (targetDir, name, markIn/Out, settings)", ""),
    "render.get_settings": (I, "deliver.list_presets (current format/codec, mode)", ""),
    "render.set_settings": (I, "deliver.add_job settings, deliver.set_format", ""),
    "render.set_om_settings": (I, "deliver.set_format", ""),
    "render.remove_item": (I, "deliver.remove_job", ""),
    "render.duplicate_item": (D, "deliver.add_job", "queue another job"),
    "render.list_templates": (I, "deliver.list_presets", ""),
    "render.status": (I, "deliver.status, deliver.list_jobs", "works while Resolve renders: percent, ETA, approximate frame, s/frame, output size"),
    "render.queue_in_ame": (N, "", "Adobe Media Encoder does not apply"),
    "render.save_template": (I, "deliver.save_preset", "confirm required"),
    "render.frame": (I, "render.frame / fu_render_frame, render.range, render.contact_sheet, render.compare", "temporary Saver; modal dismissed; file verified; preview inline"),
    # shape
    "shape.add_group": (D, "shape.combine (sMerge)", "shape trees merge instead of groups"),
    "shape.add_rect": (I, "shape.add (rectangle)", ""),
    "shape.add_ellipse": (I, "shape.add (ellipse)", ""),
    "shape.add_fill": (I, "shape.add (color)", "fill = the shape's color"),
    "shape.add_path": (D, "mask.add_polygon", "free paths: Polyline masks (sPolygon needs a paste as well)"),
    "shape.add_trim_paths": (I, "shape.set_trim", "WritePosition/WriteLength"),
    "shape.add_merge_paths": (I, "shape.combine (sBoolean)", ""),
    "shape.add_stroke": (I, "shape.add (strokePx), shape.modify sOutline", ""),
    "shape.add_polystar": (I, "shape.add (star | ngon)", ""),
    "shape.add_repeater": (I, "shape.modify sDuplicate", ""),
    "shape.add_rounded_corners": (I, "shape.add (radiusPx)", "rectangles; other shapes n/a"),
    "shape.add_offset_paths": (I, "shape.modify sExpand", ""),
    "shape.add_wiggle_paths": (I, "shape.modify sJitter (point offsets)", ""),
    "shape.add_zigzag": (N, "", "no sShape zigzag"),
    "shape.add_pucker_bloat": (N, "", "no sShape pucker/bloat"),
    "shape.add_twist": (N, "", "no sShape twist"),
    "shape.add_gradient_fill": (D, "shape.render + Background gradient via merge.set_matte", "sShapes are solid; gradient = gradient Background matted by the shape"),
    "shape.add_gradient_stroke": (D, "as gradient fill", ""),
    "shape.add_wiggle_transform": (I, "shape.modify sJitter (shape offsets)", ""),
    # text
    "text.set_content": (I, "text.set_content", ""),
    "text.set_style": (I, "text.set_style", "font/style/size(px)/color/tracking/leading/justify, verified"),
    "text.set_style_range": (D, "text.add_follower (per-character)", "Text+ styles the whole block; per-character via Follower / shading elements"),
    "text.measure": (I, "tool.bounds", "rendered or DoD box"),
    "text.set_box": (D, "input.set LayoutType/LayoutWidth/LayoutHeight/Wrap", "Text Box layout inputs"),
    "text.set_variable_font": (N, "", "no variable-axis inputs on Text+"),
    "text.add_font_axis": (N, "", "as above"),
    "text.add_animator": (I, "text.add_follower", "Follower = animator + range selector"),
    "text.paste_range": (N, "", "no rich-text range API"),
    "text.reset_style": (D, "input.set to TSV defaults (effect.inputs)", ""),
    # timeline (AE comp timeline UI)
    "timeline.set_time": (I, "comp.set_time", ""),
    "timeline.set_active_comp": (I, "comp.set_current", "timeline + playhead + Fusion page + identity check"),
    "timeline.select_layers": (I, "tool.select", ""),
    # transform
    "transform.set": (I, "transform.set", "px/normalized, degrees, 3D Transform3DOp"),
    # viewer
    "viewer.get_state": (I, "viewer.get_state", ""),
    "viewer.set_options": (D, "viewer.view", "show a tool in a viewer; zoom/exposure/guides are UI state"),
}

LORD = {  # lordhoell/davinci-resolve-mcp Fusion functions -> ours
    "fusion_get_current_comp": "comp.info / fu_comp_info", "fusion_get_comp_from_timeline_item": "comp ref {timeline, item, comp}",
    "fusion_get_comp_by_name": "comp ref {comp: name}", "comp_add_tool": "tool.add", "comp_find_tool": "tool.info", "comp_find_tool_by_type": "tool.list (regId)",
    "comp_get_tool_list": "tool.list", "comp_start_undo": "automatic per call", "comp_end_undo": "automatic per call", "comp_undo": "comp.undo", "comp_redo": "comp.redo",
    "comp_get_attrs": "comp.info", "comp_set_active_tool": "tool.select", "comp_get_current_time": "comp.info", "comp_set_current_time": "comp.set_time",
    "comp_render": "render.frame / render.range", "comp_abort_render": "render.cancel", "comp_is_rendering": "render ops block until done; render.cancel reports it",
    "comp_play": "n/a (UI playback)", "comp_stop": "n/a (UI playback)", "comp_lock": "automatic around AddTool", "comp_unlock": "automatic", "comp_is_locked": "comp.info (locked)",
    "comp_copy_settings": "setting.copy", "comp_paste": "setting.paste", "comp_save": "comp.export_file", "comp_get_data": "data.get", "comp_set_data": "data.set",
    "comp_get_prefs": "pref.get", "comp_set_prefs": "pref.set", "comp_get_next_key_time": "keyframe.list", "comp_get_prev_key_time": "keyframe.list",
    "comp_get_frame_list": "n/a", "comp_get_console_history": "n/a", "comp_execute": "eval.lua (opt-in)", "comp_map_path": "n/a", "comp_reverse_map_path": "n/a",
    "comp_get_comp_path_map": "n/a", "comp_set_loop": "n/a (UI playback)", "comp_get_flow_view": "tool.set_position",
    "flow_set_pos": "tool.set_position", "flow_get_pos": "tool.set_position (readback)", "flow_queue_set_pos": "tool.set_position", "flow_flush_set_pos_queue": "tool.set_position",
    "flow_select": "tool.select", "flow_frame_all": "n/a (UI)", "flow_get_scale": "n/a (UI)", "flow_set_scale": "n/a (UI)",
    "input_get_attrs": "input.list", "input_get_expression": "input.get / expression.list", "input_set_expression": "expression.set", "input_connect_to": "input.connect / input.link",
    "input_get_connected_output": "input.get (source)", "input_get_keyframes": "keyframe.list", "input_get_tool": "tool.info", "input_hide_view_controls": "n/a (UI)",
    "input_hide_window_controls": "n/a (UI)", "input_view_controls_visible": "n/a (UI)", "input_window_controls_visible": "n/a (UI)", "input_get_data": "data.get",
    "fusion_get_version": "fu_version_info", "fusion_get_global_path_map": "n/a", "fusion_get_prefs": "pref.get (app)", "fusion_get_reg_list": "effect.list_available",
    "fusion_get_reg_attrs": "effect.inputs", "fusion_get_font_list": "font.list", "fusion_cache_get_size": "n/a", "fusion_cache_purge": "n/a", "fusion_cache_free_space": "n/a",
    "loader_set_multi_clip": "media.add_loader / media.replace", "polyline_mask_get_bezier_polyline": "setting.copy (mask)",
    "output_get_attrs": "tool.info (outputs)", "output_get_value": "render.frame", "output_get_connected_inputs": "tool.info (consumers)", "output_get_dod": "tool.bounds (dod)",
    "output_enable_disk_cache": "n/a", "output_clear_disk_cache": "n/a", "output_get_tool": "tool.info", "output_get_data": "data.get",
    "spline_get_keyframes": "keyframe.list", "spline_set_keyframes": "keyframe.add", "spline_delete_keyframes": "keyframe.remove", "spline_adjust_keyframes": "keyframe.shift",
    "spline_get_spline_from_input": "keyframe.list (spline)", "tool_get_attrs": "tool.info", "tool_get_name": "tool.info", "tool_get_id": "tool.info (regId)",
    "tool_get_input_list": "input.list", "tool_get_output_list": "tool.info (outputs)", "tool_set_input": "input.set", "tool_get_input": "input.get", "tool_connect_input": "input.connect",
    "tool_disconnect_input": "input.disconnect", "tool_add_modifier": "modifier.add", "tool_save_settings": "setting.copy", "tool_load_settings": "setting.paste",
    "tool_delete": "tool.delete", "tool_refresh": "internal (input.add_control)", "tool_get_keyframes": "keyframe.list", "tool_get_data": "data.get", "tool_set_data": "data.set",
    "tool_get_control_page_names": "input.list", "tool_set_tile_color": "tool.set_attrs (tileColor)", "tool_set_text_color": "n/a (UI)",
}

TOOLS = [("ae_get_skill", "fu_get_skill", "serves fusion-* skills from ~/.agents/skills, sha256 manifest"),
         ("ae_get_skill_asset", "fu_get_skill_asset", "hash-verified path"),
         ("ae_project_info", "fu_project_info", ""), ("ae_comp_info", "fu_comp_info", ""), ("ae_layer_info", "fu_tool_info", "inputs, values, wiring, modifiers, keyframes, expressions"),
         ("ae_render_frame", "fu_render_frame", "temporary Saver PNG; modal auto-dismissed; file verified; preview returned inline as an image"),
         ("ae_project_export_json", "fu_do scene.export / fu_comp_export", "scene.export reads a scene-builder comp back as its layer-level JSON (+ drift); fu_comp_export gives .setting text and tool JSON"), ("ae_version_info", "fu_version_info", ""),
         ("ae_context", "fu_context", "project/timeline/page/comp + live-verified rules"), ("ae_catalog", "fu_catalog", ""), ("ae_do", "fu_do", "+ dryRun"),
         ("ae_save_project", "fu_do project.save", ""), ("ae_project_import_json", "fu_do scene.build / setting.paste / comp.import_file", "scene.build: one layer-level JSON -> a native graph in one quiet paste; scene.update edits it by layer id")]

BETTER = [
    "Every Resolve call is serialized through ONE worker process behind ONE lock: parallel MCP tool calls cannot interleave inside Resolve (the AE connector let two scripts run at once and AE raised a blocking 'second script was not run' modal).",
    "Timeouts kill the worker and report TIMEOUT with uncertain: true and a re-read-state hint (same contract as ae_do), and the next call gets a fresh worker.",
    "Every call starts with a UI check: a modal that makes Resolve return None is reported as UI_BLOCKED, never as empty state; during a Deliver render calls return RENDERING while deliver.status/deliver.stop/system.memory keep working; Resolve's render modals are auto-dismissed (switchable).",
    "See-your-own-work loop: fu_render_frame / render.frame return the preview INLINE as an MCP image (ae_render_frame is file-only, so the agent needs a second read); render.contact_sheet puts a whole motion in one labeled grid; render.compare scores a frame against a reference (AE render at the same beat) with MAE, PSNR, SSIM and a diff panel; audit.motion checks timing/easing/stagger numerically with subframe sampling.",
    "fu_do dryRun validates and policy-checks without touching Resolve; parent-side TSV checks catch unknown reg IDs, input IDs and ComboID options (with suggestions) before any call.",
    "Built for film-scale work after a cold rebuild of a 25 s AE ad (gap-fix pass): exact-length Fusion items on any track (timeline.add_fusion_clip), custom timeline format, project.load after a restart, quiet bulk pastes/deletes/clears, responses over the MCP budget spilled to a file with a preview, paged skill reads, MediaOut1 isolation during renders, render.cancel cleanup, Deliver progress/stop during a render, and Resolve memory in fu_context and render results.",
    "Scene builder hardened by a cold rebuild of the same ad through one film comp (rematch pass): in/out is cut frame-exact on the layer's Blend (the culling region and its margin never show a layer outside in/out), pastes diff tool names inside Fusion (no per-existing-tool bridge reads, so paste time stops growing with the comp), one asset at two scales gets per-variant tool names, non-uniform scale keeps a supersampled container's texture scale, text masks take box [x, y, w, h] or corners [x0, y0, x1, y1] with a coverage warning, size animation motion-blurs, and quiet build/plan replies are counts plus a detail file.",
    "Encoded live-verified rules (auto-connect trap, paste on the current Fusion-page comp, deferred Execute polling, stray-key removal, SetExpression(None), measured units, pasted defaults) instead of documentation only.",
]


def main():
    ae = json.load(open(os.path.join(ROOT, "study", "ae_ops.json"), encoding="utf-8"))
    from fusion_connector.ops import OPS
    res_path = os.path.join(ROOT, "tests", "smoke_results.json")
    smoke = json.load(open(res_path, encoding="utf-8")) if os.path.exists(res_path) else {"results": {}, "when": None}
    R = smoke["results"]
    gpath = os.path.join(ROOT, "tests", "gapfix_live_results.json")  # gap-fix live pass: newer evidence for the ops it touched
    if os.path.exists(gpath):
        G = json.load(open(gpath, encoding="utf-8"))
        agg = {}
        for k, v in G.items():
            if k.startswith("_") or not isinstance(v, dict) or (v.get("evidence") or {}).get("superseded"):
                continue  # superseded records (the heavy Deliver tests that crashed Resolve) are reported in GAPFIX.md
            op = max((o for o in list(OPS) + [t[1] for t in TOOLS] if k == o or k.startswith(o + ".")), key=len, default=None)
            if op:
                agg.setdefault(op, []).append(v["status"])
        for op, sts in agg.items():
            R[op] = {"status": "fail" if "fail" in sts else "pass", "runs": len(sts), "gapfix": True,
                     "failures": [{"error": "gap-fix live check failed (tests/gapfix_live_results.json)"}] if "fail" in sts else []}
    missing = [o["name"] for o in ae if o["name"] not in MAP]
    assert not missing, f"unmapped AE ops: {missing}"
    import re
    OPRE = re.compile(r"\b(?:fu_[a-z_]+|[0-9a-z]+\.[a-z_]+)\b")
    for k, (st, fu, _) in MAP.items():
        for part in OPRE.findall(fu):
            assert part in OPS or part.startswith("fu_"), f"{k} maps to unknown op {part}"

    def st_of(fu):
        ops = [o for o in OPRE.findall(fu) if o in OPS or o.startswith("fu_")]
        if not ops:
            return ""
        sts = [R.get(o, {}).get("status", "untested") for o in ops]
        return "fail" if "fail" in sts else ("pass" if all(s == "pass" for s in sts) else ("partly tested" if "pass" in sts else "untested"))

    counts = {I: 0, D: 0, N: 0}
    for st, _, _ in MAP.values():
        counts[st] += 1
    tested = [o for o in OPS if R.get(o, {}).get("status") == "pass"]
    failed = [o for o in OPS if R.get(o, {}).get("status") == "fail"]
    untested = [o for o in OPS if o not in R]
    L = ["# PARITY: Higgsfield use-after-effects -> Use Fusion", "",
         f"Generated by `scripts/parity.py` from `study/ae_ops.json` (197 AE operations, offline registry dump of fnf-after-effects-mcp 0.1.3), "
         f"the live Fusion catalog ({len(OPS)} operations) and `tests/smoke_results.json` (live smoke run {smoke.get('when')}, project Testbed).", "",
         "## Summary", "",
         f"- AE operations mapped: {len(MAP)} of 197: **{counts[I]} implemented**, **{counts[D]} different model** (the Fusion way, with the op to use), **{counts[N]} n/a** (reason given).",
         f"- Fusion catalog: {len(OPS)} operations in {len({o.category for o in OPS.values()})} categories; live smoke: **{len(tested)} pass**, **{len(failed)} fail**, **{len(untested)} untested**.",
         "- Tools: all 11 AE tools mirrored (plus save/import through fu_do).", "",
         "## Where Use Fusion does better than the AE connector", ""] + [f"- {b}" for b in BETTER] + [
         "", "## Tools", "", "| AE tool | Use Fusion | Notes | Live |", "|---|---|---|---|"]
    for a, f, n in TOOLS:
        L.append(f"| `{a}` | `{f}` | {n} | {R.get(f.split(' ')[0], {}).get('status', '') if f.startswith('fu_') else ''} |")
    L += ["", "## Operations (every AE operation)", "", "| AE operation | Status | Fusion operation(s) | Note | Live |", "|---|---|---|---|---|"]
    for o in ae:
        st, fu, note = MAP[o["name"]]
        L.append(f"| `{o['name']}` | {st} | {('`' + fu + '`') if fu else ''} | {note} | {st_of(fu) if fu else ''} |")
    L += ["", "## Fusion catalog with live smoke status", "", "| Operation | Category | Live | Evidence |", "|---|---|---|---|"]
    for name in sorted(OPS):
        r = R.get(name)
        ev = ""
        if r and r["status"] == "fail":
            ev = json.dumps(r["failures"][0].get("error"), default=str)[:160].replace("|", "/")
        elif r:
            ev = f"{r['runs']} run(s)" + (" (gap-fix live pass)" if r.get("gapfix") else "")
        L.append(f"| `{name}` | {OPS[name].category} | {r['status'] if r else 'untested'} | {ev} |")
    extra = sorted(k for k in R if k not in OPS)
    if extra:
        L += ["", "### Tool-level and policy checks", "", "| Check | Live |", "|---|---|"] + [f"| `{k}` | {R[k]['status']} |" for k in extra]
    L += ["", "## Second comparison: lordhoell/davinci-resolve-mcp (MIT) Fusion tools", "",
          "Their 104 Fusion functions are thin 1:1 API wrappers keyed by object IDs (no validation, no verified rules). Ours is a superset where it makes sense; UI-only calls are n/a.", "",
          "| lordhoell function | Use Fusion |", "|---|---|"]
    names = [l.strip() for l in open(os.path.join(ROOT, "prior-art", "lordhoell_fusion_tools.txt"))] if os.path.exists(os.path.join(ROOT, "prior-art", "lordhoell_fusion_tools.txt")) else sorted(LORD)
    names = [n for n in names if not n.startswith("_") and n not in ("ok", "err")]
    for n in names:
        L.append(f"| `{n}` | {LORD.get(n, 'helper')} |")
    L += ["", "Other prior art: samuelgursky/davinci-resolve-mcp guarded kernel (dry run, Lock around writes, per-input readback, validated connect) is matched by fu_do dryRun, readback on every set, and checked connect; CiprianSpiridon's offline .comp parser is matched by setting.validate (vendored parser from our skill build); apvlv's node chains by merge.stack / effect.add.", ""]
    open(os.path.join(ROOT, "PARITY.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"PARITY.md: {counts}, live pass {len(tested)}, fail {len(failed)}, untested {len(untested)}")


if __name__ == "__main__":
    main()
