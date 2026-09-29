# Geometry and hierarchy

## Coordinates

- Use the frame's local size, not rotated document bounds. Express each node in the frame canvas:
  compose its absolute transform with the inverse of the frame's absolute transform. Never assume a
  captured `relativeTransform` already targets the retained parent.
- Figma: x right, y down, origin top-left, px. Fusion: normalized per image, y up, origin bottom-left.
  Convert after all affine math is done in px: points `x/W`, `1 - y/H`; vectors (handles, offsets)
  `dx/W`, `-dy/H`. Transform vertices with the full affine matrix and handles with its linear part only.
- Rotation and scale: bake them into converted geometry for static shapes (exact, keeps shear), or map
  to a Transform (`Angle` degrees, positive counterclockwise, so negate Figma's clockwise-down angle;
  `Size`/`Aspect`) when the node must stay a movable unit. Keep shear in geometry; a Transform cannot
  express it without a `CornerPositioner`.
- Anchor: Figma rotates about the node's top-left origin; a Fusion Transform rotates about `Pivot`. Put
  `Pivot` at the node's origin in canvas coordinates, or bake the rotation, exactly once.

## Hierarchy

- Frame canvas at the root (main skill). Retained Figma groups/frames become Fusion Groups
  (`GroupOperator`) or unit subgraphs ending in one Merge and one Transform (design-first unit contract),
  at most four levels deep. Flatten deeper organizational containers into the nearest retained parent,
  keeping editable children and their IDs. Auto Layout needs no wrapper: its result is already in the
  absolute positions. Report any scope that cannot fit without a material tradeoff.
- Sibling order = Merge order: the first child is the bottom Background, each later child a Foreground
  merged on top, preserving mask scopes.

## No precomp cropping in Fusion

AE crops each new precomp to its visible bounds and then compensates parent positions. Fusion does not
need this: every unit renders on the frame canvas and the Domain of Definition limits computation to its
real pixels, so there is no crop, no anchor compensation and no double shift. Keep every unit at frame
canvas size unless a unit must later be reused elsewhere at its own size; then give that unit its own
`Background` canvas and place it with a Merge `Center` computed from its bounds, and verify it renders in
place.

## Checks

Parent appearance unchanged, canvas size unchanged, nothing clipped at canvas edges (effects extend
outside shapes: check shadows and blurs), no leftover helper tools, no Merge without Background, and no
expression or `SourceOp` pointing outside the import.
