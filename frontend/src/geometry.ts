export type Box = { x: number; y: number; w: number; h: number };

// Keep the chosen size and move an overflowing region back inside the source.
// backend.core.normalize_box uses the same normalized-coordinate specification.
export function normalizeBox(box: Box): Box {
  if (!Object.values(box).every(Number.isFinite) ||
      box.x < 0 || box.x > 1 || box.y < 0 || box.y > 1 ||
      box.w < .01 || box.w > 1 || box.h < .01 || box.h > 1) {
    throw new Error('Use posições de 0 a 1 e dimensões de 0,01 a 1.');
  }
  return { ...box, x: Math.min(box.x, 1 - box.w), y: Math.min(box.y, 1 - box.h) };
}

export function cropPixels(box: Box, width: number, height: number) {
  const b = normalizeBox(box);
  const w = Math.max(2, Math.floor(width * b.w / 2) * 2);
  const h = Math.max(2, Math.floor(height * b.h / 2) * 2);
  return { w, h,
    x: Math.min(width - w, Math.floor(width * b.x / 2) * 2),
    y: Math.min(height - h, Math.floor(height * b.y / 2) * 2) };
}
