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

export type Point = {x: number; y: number};
const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));

export function boxFromPoints(a: Point, b: Point): Box {
  const left = clamp(Math.min(a.x,b.x),0,1);
  const top = clamp(Math.min(a.y,b.y),0,1);
  return normalizeBox({x:left,y:top,
    w:clamp(Math.max(a.x,b.x),0,1)-left < .01 ? .01 : clamp(Math.max(a.x,b.x),0,1)-left,
    h:clamp(Math.max(a.y,b.y),0,1)-top < .01 ? .01 : clamp(Math.max(a.y,b.y),0,1)-top});
}

export function moveBox(box: Box, dx: number, dy: number): Box {
  const b=normalizeBox(box);
  return {...b,x:clamp(b.x+dx,0,1-b.w),y:clamp(b.y+dy,0,1-b.h)};
}

export function resizeBox(box: Box, corner: string, point: Point): Box {
  const b=normalizeBox(box);
  const right=b.x+b.w, bottom=b.y+b.h;
  const x=corner.includes('w')?clamp(point.x,0,right-.01):b.x;
  const y=corner.includes('n')?clamp(point.y,0,bottom-.01):b.y;
  return normalizeBox({x,y,
    w:Math.max(.01,(corner.includes('e')?clamp(point.x,b.x+.01,1):right)-x),
    h:Math.max(.01,(corner.includes('s')?clamp(point.y,b.y+.01,1):bottom)-y)});
}

export function roundBox(box: Box): Box {
  return normalizeBox(Object.fromEntries(Object.entries(box).map(([key,value])=>[key,Math.round(value*10000)/10000])) as Box);
}
