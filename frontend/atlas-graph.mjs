// Display adapters only: the saved coordinates and ordered neighbours stay read-only.
export function buildAtlasGraph(positions, adjacency) {
  if (!positions.length || positions.length !== adjacency.length) throw new Error("Incomplete Atlas graph.");
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  positions.forEach(position => {
    if (position.length !== 3 || !position.every(Number.isFinite)) throw new Error("Invalid Atlas position.");
    position.forEach((value, axis) => { min[axis] = Math.min(min[axis], value); max[axis] = Math.max(max[axis], value); });
  });
  const center = min.map((value, axis) => (value + max[axis]) / 2);
  const scale = 200 / Math.max(...max.map((value, axis) => value - min[axis]), 1);
  const base = new Float32Array(positions.length * 3);
  const nodes = positions.map((position, id) => {
    const [x, y, z] = position.map((value, axis) => (value - center[axis]) * scale);
    base.set([x, y, z], id * 3);
    return { id, x, y, z, fx: x, fy: y, fz: z };
  });
  const endpoints = new Uint32Array(adjacency.reduce((n, row) => n + row.length, 0) * 2);
  adjacency.forEach((neighbors, source) => {
    if (neighbors.length !== 25 || new Set(neighbors).size !== 25) throw new Error("A recording needs 25 unique neighbours.");
    neighbors.forEach((target, rank) => {
      if (!Number.isInteger(target) || target < 0 || target >= nodes.length || target === source) throw new Error("Invalid Atlas connection.");
      const offset = (source * 25 + rank) * 2;
      endpoints[offset] = source; endpoints[offset + 1] = target;
    });
  });
  return { nodes, base, endpoints };
}
