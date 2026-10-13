import React from "react";
import { createRoot } from "react-dom/client";
import { ForceAtlas } from "./ForceAtlas.jsx";

const mounted = new WeakMap();
export default function ({ parentElement, data, setTriggerValue }) {
  const element = parentElement.querySelector(".atlas-map");
  let entry = mounted.get(element);
  if (!entry) {
    entry = { root: createRoot(element) };
    mounted.set(element, entry);
  }
  const viewKey = data.view_key ?? "original";
  if (entry.viewKey !== viewKey) {
    Object.assign(entry, { viewKey, positions: data.positions, adjacency: data.adjacency, bands: data.bands });
  }
  const focusId = data.focused && data.selected !== null ? `${data.revision}-${data.selected}` : null;
  if (entry.focusId !== focusId) {
    entry.focusId = focusId;
    entry.focusKey = focusId === null ? null : { ids: [data.selected, ...data.neighbors], at: focusId };
  }
  entry.root.render(<ForceAtlas key={viewKey} positions={entry.positions} adjacency={entry.adjacency} bands={entry.bands}
    selected={data.selected} matches={data.matches} labels={data.labels}
    focusKey={entry.focusKey} resetKey={data.revision} onSelect={index => setTriggerValue("picked", index)} />);
  return () => queueMicrotask(() => {
    if (!element.isConnected) { entry.root.unmount(); mounted.delete(element); }
  });
}
