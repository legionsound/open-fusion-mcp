# Reuse and updates

## Verified unchanged repeat

- Running the transfer again makes a new, separate import. Skip the rebuild only when the source is
  untouched and the earlier graph was verified, its media is stored durably and every node is mapped:
  compare the file version, node fingerprints, child order, media hashes, timing and hierarchy policy
  with the record, and make sure the saved `.setting`/`.comp` is the one that was verified. The mere
  presence of a cache file proves nothing.
- Paste the verified `.setting` into the new comp with a new unique prefix (collisions rename with `_1`,
  realities §9), validate media paths (Loader `Clip` or MediaIn), and rebind the map to the new tool
  names. Copying media files does not relink Loaders by itself.
- Compare a native render with the previously verified render under the same conditions, then run the
  shared audit. A match to the cached render proves consistency with that render, not equivalence to
  Figma; report any tolerance used.
- Any mismatch in source, metadata, dependencies or verification: take the fresh route. Creating a
  reusable standalone template needs an explicit request (a macro in the Templates folder, or a saved
  `.setting`); otherwise say cache creation is not set up.

## Explicit mapped update

- An update needs the requested destination and a map from source IDs to real Fusion tools. Match by
  ID (tool name prefix `FG_n<id>`), never by display name; if the map is missing or ambiguous, resolve
  the target before mutating and never silently replace the import.
- Capture fresh source state; compare geometry, text, styles, media, visibility and child order with the
  mapped version. Find inputs that were animated or edited in Fusion since the import (splines on
  inputs, expressions, changed values vs the recorded import values). Change only what was asked for
  and leave other animation and the user's own edits alone; ask only if a change in the source clashes
  with those edits and the request does not say which one wins.
- Before structural replacement export the comp. A node that disappeared in Figma does not authorize
  deleting an animated tool. Update polylines by rewriting the `Polyline` value only when no shape keys
  exist; with shape keys, report the conflict.
- Reconcile Merge order and mask dependencies, verify affected appearance in the full frame and audit
  the graph. Update fingerprints, tool identities and verification state only for completed changes;
  keep explicit partial status for unresolved nodes.
