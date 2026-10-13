import React, { useEffect, useMemo, useRef, useState } from "react";
import { ForceGraph3D, THREE, createForceWorker } from "./force-graph.mjs";
import { buildAtlasGraph } from "./atlas-graph.mjs";

const palette = ["#638dff", "#32cfb5", "#ffa66b"];
// The complete graph is rendered below as batched geometry. The library's hidden
// link objects otherwise get scanned for particles on every animation frame.
const rendererGraph = { nodes: [], links: [] };
const styles = `
.force-atlas{--fg-text:#e7eef9;--fg-muted:#aabbd2;--fg-surface:#192c47;--fg-border:#354965;--fg-accent:#a9caff;min-width:0;color:var(--fg-text);font:14px/1.5 "Noto Sans", "Noto Sans Bengali",sans-serif;background:#122239;border-radius:12px;isolation:isolate}
.force-atlas[data-force-theme=light]{--fg-text:#203451;--fg-muted:#566981;--fg-surface:#f4f7fc;--fg-border:#ccd7e6;--fg-accent:#285cb1;background:#edf2fa}
.force-atlas-tools{position:relative;display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:7px 9px;border-bottom:1px solid var(--fg-border);font-size:13px;line-height:1.4}
.force-atlas-tools button,.force-atlas-tools select,.force-atlas-options summary{font:inherit;color:inherit;background:transparent;border:1px solid var(--fg-border);border-radius:5px;padding:4px 8px;min-height:28px;cursor:pointer}
.force-atlas-tools button:hover,.force-atlas-options summary:hover{background:var(--fg-surface)}
.force-atlas-layout{display:flex;border:1px solid var(--fg-border);border-radius:6px;overflow:hidden}
.force-atlas-layout button{border:0;border-radius:0;min-width:50px}
.force-atlas-tools button[aria-pressed=true]{background:var(--fg-accent);color:#152a47;border-color:var(--fg-accent)}
.force-atlas-tools button:disabled{opacity:.4;cursor:default}
.force-atlas-tools :focus-visible{outline:2px solid var(--fg-accent);outline-offset:3px}
.force-atlas-spacer{flex:1}
.force-atlas-options summary{list-style:none}
.force-atlas-options summary::-webkit-details-marker{display:none}
.force-atlas-options summary:after{content:"⌄";padding-left:8px}
.force-atlas-options[open] summary{background:var(--fg-surface)}
.force-atlas-options-panel{position:absolute;z-index:4;right:9px;top:calc(100% + 6px);width:min(310px,calc(100vw - 60px));display:grid;gap:12px;padding:14px;border:1px solid var(--fg-border);border-radius:8px;background:var(--fg-surface);box-shadow:0 12px 28px rgb(0 0 0 / .18)}
.force-atlas-options-panel label{display:flex;align-items:center;justify-content:space-between;gap:12px}
.force-atlas-options-panel select{min-width:150px;max-width:60%;background:var(--fg-surface)}
.force-atlas-options-panel input[type=range]{width:135px;accent-color:var(--fg-accent)}
.force-atlas-options-panel input[role=switch]{appearance:none;position:relative;flex:none;width:28px;height:16px;margin:0;border:1px solid var(--fg-border);border-radius:16px;background:transparent;cursor:pointer}
.force-atlas-options-panel input[role=switch]:before{content:"";position:absolute;left:2px;top:2px;width:10px;height:10px;border-radius:50%;background:var(--fg-muted)}
.force-atlas-options-panel input[role=switch]:checked{background:var(--fg-accent);border-color:var(--fg-accent)}
.force-atlas-options-panel input[role=switch]:checked:before{left:14px;background:#152a47}
.force-atlas-options-panel .force-atlas-option-actions{display:flex;flex-wrap:wrap;gap:8px}
.force-atlas-options-panel p{margin:0;color:var(--fg-muted);font-size:12px;line-height:1.6}
.force-atlas-viewport{position:relative;height:clamp(320px,calc(100dvh - 390px),720px);min-height:320px;overflow:hidden;background:inherit}
.force-atlas-viewport canvas{display:block;touch-action:none;cursor:grab}
.force-atlas-tooltip{position:absolute;left:14px;bottom:14px;max-width:min(370px,calc(100% - 28px));padding:10px 14px;border:1px solid var(--fg-border);border-radius:8px;background:var(--fg-surface);color:var(--fg-text);pointer-events:none;overflow-wrap:anywhere;font-family:"Noto Sans Bengali","Noto Sans",sans-serif}
.force-atlas-tooltip div{font-size:12px;color:var(--fg-muted);margin-top:3px}
.force-atlas-status{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;padding:9px 14px;font-size:12px;font-variant-numeric:tabular-nums;color:var(--fg-muted);border-top:1px solid var(--fg-border)}
.force-atlas-status output{margin-left:auto;color:var(--fg-text)}
.force-atlas-motion-note{margin:0;padding:0 14px 10px;font-size:12px;color:var(--fg-muted)}
.force-atlas-error{padding:16px;color:#ffca9b}
.force-atlas:fullscreen{display:flex;flex-direction:column;height:100vh;border-radius:0}
.force-atlas:fullscreen .force-atlas-viewport{flex:1;height:auto;min-height:0}
@media(max-width:600px){.force-atlas-tools{gap:5px;padding:7px}.force-atlas-spacer{display:none}.force-atlas-viewport{height:52vh;min-height:300px}.force-atlas-status{font-size:11px;padding:9px}.force-atlas-options-panel{right:8px}}
@media(pointer:coarse){.force-atlas-tools button,.force-atlas-options summary,.force-atlas-tools select{min-height:36px;padding:6px 9px}}
@media(prefers-reduced-motion:reduce){.force-atlas *{scroll-behavior:auto}}
`;

class GraphBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div role="status" className="force-atlas-error">The 3D graph could not start. Search and the 25-neighbour list remain available. Reload to try again.</div> : this.props.children;
  }
}

export function ForceAtlas(props) {
  return <GraphBoundary><Graph {...props} /></GraphBoundary>;
}

function Graph({ positions, adjacency, bands, selected = null, matches = [], labels = {}, theme = "dark",
  focusKey, resetKey = 0, onSelect }) {
  const graph = useMemo(() => buildAtlasGraph(positions, adjacency), [positions, adjacency]);
  const graphRef = useRef(null), viewport = useRef(null), wrapper = useRef(null), engine = useRef(null), workerRef = useRef(null);
  const callback = useRef(onSelect), live = useRef({ selected, matches, labels, bands });
  callback.current = onSelect; live.current = { selected, matches, labels, bands };
  const [size, setSize] = useState({ width: 600, height: 480 });
  const [layout, setLayout] = useState("atlas"), [running, setRunning] = useState(false), [step, setStep] = useState(0);
  const [links, setLinks] = useState("all"), [opacity, setOpacity] = useState(0.025), [pointSize, setPointSize] = useState(3);
  const [rotate, setRotate] = useState(false), [hovered, setHovered] = useState(null), [error, setError] = useState("");
  const [quality, setQuality] = useState("auto");
  const [blackBackground, setBlackBackground] = useState(false);
  const backgroundColor = blackBackground ? "#000000" : theme === "dark" ? "#122239" : "#edf2fa";
  const [rendered, setRendered] = useState({ points: 0, links: 0, fps: 0 });
  const rendererConfig = useMemo(() => ({ antialias: false, powerPreference: "high-performance" }), []);

  function fit(ids) {
    const api = graphRef.current;
    if (!api || !engine.current) return;
    const nodes = ids ? ids.map(id => graph.nodes[id]).filter(Boolean) : graph.nodes;
    if (!nodes.length) return;
    const bounds = new THREE.Box3();
    nodes.forEach(node => bounds.expandByPoint(new THREE.Vector3(node.x, node.y, node.z)));
    const target = bounds.getCenter(new THREE.Vector3()), extent = bounds.getSize(new THREE.Vector3());
    const camera = api.camera(), aspect = Math.max(viewport.current.clientWidth / viewport.current.clientHeight, 0.2);
    const distance = Math.max(extent.y, extent.x / aspect, extent.z, 5) / (2 * Math.tan(camera.fov * Math.PI / 360)) * 1.45;
    const direction = camera.position.clone().sub(api.controls().target).normalize();
    if (!direction.length()) direction.set(0.3, 0.2, 1).normalize();
    const position = target.clone().addScaledVector(direction, distance);
    api.cameraPosition(position, target, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600);
  }

  function updateFocus() {
    const current = engine.current;
    if (!current) return;
    const { selected: choice, matches: results, bands: colors } = live.current;
    const neighbors = new Set(choice === null ? [] : adjacency[choice]);
    const matching = new Set(results), active = choice !== null || matching.size > 0;
    const array = current.colors.array;
    graph.nodes.forEach((node, i) => {
      const color = new THREE.Color(i === choice ? "#ffda85" : neighbors.has(i) ? "#ff74b6" : matching.has(i) ? "#72e6ff" : palette[colors[i]] ?? "#638dff");
      if (active && i !== choice && !neighbors.has(i) && !matching.has(i)) color.multiplyScalar(0.25);
      array.set([color.r, color.g, color.b], i * 3);
    });
    current.colors.needsUpdate = true;
    const ids = choice === null ? [] : [choice, ...adjacency[choice]];
    current.focusIds = ids;
    current.focusGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(ids.length * 3), 3));
    current.focusGeometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(ids.flatMap(id => {
      const color = new THREE.Color(id === choice ? "#ffda85" : "#ff74b6"); return [color.r, color.g, color.b];
    })), 3));
    current.focusLines.setAttribute("position", new THREE.BufferAttribute(new Float32Array(Math.max(ids.length - 1, 0) * 6), 3));
    current.dirty = true;
  }

  useEffect(() => {
    const host = viewport.current;
    const resize = () => setSize({ width: Math.max(host.clientWidth, 1), height: Math.max(host.clientHeight, 1) });
    const observer = new ResizeObserver(resize); observer.observe(host); resize();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const api = graphRef.current, host = viewport.current;
    const scene = api.scene(), renderer = api.renderer();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1));
    const pointGeometry = new THREE.BufferGeometry(), lineGeometry = new THREE.BufferGeometry();
    const points = new THREE.BufferAttribute(new Float32Array(graph.base), 3).setUsage(THREE.DynamicDrawUsage);
    const colors = new THREE.BufferAttribute(new Float32Array(graph.base.length), 3);
    pointGeometry.setAttribute("position", points); pointGeometry.setAttribute("color", colors);
    lineGeometry.setAttribute("position", points);
    lineGeometry.setIndex(new THREE.BufferAttribute(graph.endpoints, 1));
    const discCanvas = document.createElement("canvas"); discCanvas.width = discCanvas.height = 32;
    const discContext = discCanvas.getContext("2d");
    discContext.fillStyle = "#fff"; discContext.beginPath(); discContext.arc(16, 16, 15, 0, Math.PI * 2); discContext.fill();
    const disc = new THREE.CanvasTexture(discCanvas);
    const material = new THREE.PointsMaterial({ size: 3, sizeAttenuation: false, vertexColors: true, map: disc, alphaTest: 0.5 });
    // Native indexed lines reuse the point buffer and GPU vertex cache for every edge.
    const lineMaterial = new THREE.LineBasicMaterial({ color: "#74b6da", transparent: true, opacity: 0.025, depthWrite: false });
    // ponytail: batched points and lines keep all 281,294 graph elements in a few draw calls.
    const cloud = new THREE.Points(pointGeometry, material), network = new THREE.LineSegments(lineGeometry, lineMaterial);
    const focusGeometry = new THREE.BufferGeometry(), focusLines = new THREE.BufferGeometry();
    const focusMaterial = new THREE.PointsMaterial({ size: 9, sizeAttenuation: false, vertexColors: true, depthTest: false, map: disc, alphaTest: 0.5 });
    const focusLineMaterial = new THREE.LineBasicMaterial({ color: "#ff74b6", transparent: true, opacity: 0.8, depthWrite: false });
    const focusCloud = new THREE.Points(focusGeometry, focusMaterial), focusNetwork = new THREE.LineSegments(focusLines, focusLineMaterial);
    [cloud, network, focusCloud, focusNetwork].forEach(object => { object.frustumCulled = false; scene.add(object); });
    focusCloud.renderOrder = 2;
    engine.current = { points, colors, pointGeometry, lineGeometry, material, lineMaterial, network,
      focusGeometry, focusLines, focusMaterial, focusLineMaterial, focusIds: [], dirty: true, target: null, step: 0, forceRunning: false };
    updateFocus();
    const pointer = new THREE.Vector2(), raycaster = new THREE.Raycaster();
    let down = null, hover = null, frame = null, frames = 0, last = performance.now(), visible = true, pendingPointer = null, lastPick = 0;
    const pick = event => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
      raycaster.params.Points.threshold = Math.max(api.camera().position.distanceTo(api.controls().target) * 0.0025, 0.35);
      raycaster.setFromCamera(pointer, api.camera());
      return raycaster.intersectObject(cloud)[0]?.index ?? null;
    };
    const move = event => {
      if (event.buttons) return;
      pendingPointer = { clientX: event.clientX, clientY: event.clientY };
    };
    const leave = () => { pendingPointer = null; hover = null; setHovered(null); };
    const press = event => { down = [event.clientX, event.clientY]; };
    const release = event => {
      if (event.button === 0 && down && Math.hypot(event.clientX - down[0], event.clientY - down[1]) < 5) {
        const id = pick(event); if (id !== null) callback.current?.(id);
      }
      down = null;
    };
    const lost = event => { event.preventDefault(); setError("The graphics connection was lost. Search and neighbour browsing remain available; reload to restore 3D."); };
    const canvas = renderer.domElement;
    canvas.addEventListener("pointermove", move); canvas.addEventListener("pointerdown", press);
    canvas.addEventListener("pointerleave", leave);
    canvas.addEventListener("pointerup", release); canvas.addEventListener("webglcontextlost", lost);
    const animate = now => {
      const current = engine.current;
      // Coalesce high-rate mouse events; raycast the full cloud at most 20 times/s.
      if (pendingPointer && now - lastPick >= 50) {
        const id = pick(pendingPointer); pendingPointer = null; lastPick = now;
        if (id !== hover) { hover = id; setHovered(id); canvas.style.cursor = id === null ? "grab" : "pointer"; }
      }
      if (current.target) {
        let difference = 0;
        for (let id = 0; id < graph.nodes.length; id++) {
          const node = graph.nodes[id];
          const offset = id * 3;
          const dx = current.target[offset] - node.x, dy = current.target[offset + 1] - node.y, dz = current.target[offset + 2] - node.z;
          difference = Math.max(difference, Math.abs(dx), Math.abs(dy), Math.abs(dz));
          node.x += dx * 0.12; node.y += dy * 0.12; node.z += dz * 0.12;
        }
        current.dirty = true;
        if (difference < 0.01) current.target = null;
      }
      if (current.dirty) {
        let radiusSquared = 0;
        for (let id = 0; id < graph.nodes.length; id++) {
          const node = graph.nodes[id], offset = id * 3;
          points.array[offset] = node.x; points.array[offset + 1] = node.y; points.array[offset + 2] = node.z;
          radiusSquared = Math.max(radiusSquared, node.x * node.x + node.y * node.y + node.z * node.z);
        }
        pointGeometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), Math.sqrt(radiusSquared));
        points.needsUpdate = true;
        const focused = focusGeometry.getAttribute("position"), connections = focusLines.getAttribute("position");
        current.focusIds.forEach((id, i) => {
          focused.array.set(points.array.subarray(id * 3, id * 3 + 3), i * 3);
          if (i) { connections.array.set(points.array.subarray(current.focusIds[0] * 3, current.focusIds[0] * 3 + 3), (i - 1) * 6);
            connections.array.set(points.array.subarray(id * 3, id * 3 + 3), (i - 1) * 6 + 3); }
        });
        if (focused) focused.needsUpdate = true; if (connections) connections.needsUpdate = true;
        current.dirty = false;
      }
      frames++;
      if (now - last >= 1000) {
        setStep(current.step);
        setRendered({ points: Math.min(renderer.info.render.points, graph.nodes.length),
          links: current.network.visible ? Math.min(renderer.info.render.lines, (graph.endpoints.length / 2)) : 0, fps: Math.round(frames * 1000 / (now - last)) });
        frames = 0; last = now;
      }
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    const visibility = () => {
      if (visible && !document.hidden) {
        api.resumeAnimation();
        if (frame === null) { last = performance.now(); frames = 0; frame = requestAnimationFrame(animate); }
        if (engine.current?.forceRunning) workerRef.current?.worker.postMessage({ type: "resume" });
      } else {
        api.pauseAnimation(); cancelAnimationFrame(frame); frame = null;
        workerRef.current?.worker.postMessage({ type: "pause" });
      }
    };
    const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; visibility(); });
    intersection.observe(host); document.addEventListener("visibilitychange", visibility);
    const initialFit = requestAnimationFrame(() => fit());
    return () => {
      cancelAnimationFrame(frame); cancelAnimationFrame(initialFit);
      intersection.disconnect(); document.removeEventListener("visibilitychange", visibility);
      canvas.removeEventListener("pointermove", move); canvas.removeEventListener("pointerdown", press);
      canvas.removeEventListener("pointerleave", leave);
      canvas.removeEventListener("pointerup", release); canvas.removeEventListener("webglcontextlost", lost);
      [cloud, network, focusCloud, focusNetwork].forEach(object => scene.remove(object));
      [pointGeometry, lineGeometry, focusGeometry, focusLines, material, lineMaterial, focusMaterial, focusLineMaterial, disc].forEach(object => object.dispose());
      if (workerRef.current) { workerRef.current.worker.terminate(); URL.revokeObjectURL(workerRef.current.url); workerRef.current = null; }
      engine.current = null;
    };
  }, [graph]);

  useEffect(() => { updateFocus(); }, [selected, matches, bands, graph]);
  useEffect(() => { if (engine.current) { engine.current.network.visible = links === "all"; engine.current.lineMaterial.opacity = opacity;
    engine.current.focusLineMaterial.opacity = links === "hidden" ? 0 : 0.8; engine.current.material.size = pointSize; } }, [links, opacity, pointSize]);
  useEffect(() => { const controls = graphRef.current?.controls(); if (controls) { controls.autoRotate = rotate; controls.autoRotateSpeed = 0.6; } }, [rotate]);
  useEffect(() => {
    const renderer = graphRef.current?.renderer();
    if (!renderer) return;
    const deviceRatio = window.devicePixelRatio || 1;
    // Keep large windows near the measured smooth render size, without removing geometry.
    const automaticRatio = Math.min(deviceRatio, 1, Math.sqrt(600000 / Math.max(size.width * size.height, 1)));
    renderer.setPixelRatio(quality === "sharp" ? Math.min(deviceRatio, 1.5) : automaticRatio * (quality === "smooth" ? 0.75 : 1));
  }, [quality, size.width, size.height]);
  useEffect(() => { if (focusKey) fit(focusKey.ids); }, [focusKey]);
  useEffect(() => { fit(); }, [resetKey]);

  function atlasLayout() {
    if (workerRef.current) { workerRef.current.worker.terminate(); URL.revokeObjectURL(workerRef.current.url); workerRef.current = null; }
    graph.nodes.forEach((node, id) => { node.x = node.fx = graph.base[id * 3]; node.y = node.fy = graph.base[id * 3 + 1]; node.z = node.fz = graph.base[id * 3 + 2]; });
    if (engine.current) { engine.current.target = null; engine.current.dirty = true; engine.current.step = 0; engine.current.forceRunning = false; }
    setLayout("atlas"); setRunning(false); setStep(0); fit();
  }
  function forceLayout() {
    if (!engine.current) return;
    try {
      if (!workerRef.current) {
        const created = createForceWorker(); workerRef.current = created;
        created.worker.onerror = () => { if (engine.current) engine.current.forceRunning = false; setError("Force layout could not start. The saved Atlas layout remains available."); setRunning(false); };
        created.worker.onmessage = ({ data }) => {
          if (workerRef.current?.worker !== created.worker) return;
          if (data.error) { if (engine.current) engine.current.forceRunning = false; setError(data.error); setRunning(false); return; }
          if (engine.current) { engine.current.target = data.positions; engine.current.step = data.step; }
          if (data.done) { if (engine.current) engine.current.forceRunning = false; setStep(data.step); setRunning(false); }
        };
        const positions = new Float32Array(engine.current.points.array), endpoints = new Uint32Array(graph.endpoints);
        created.worker.postMessage({ type: "start", positions, endpoints }, [positions.buffer, endpoints.buffer]);
      } else workerRef.current.worker.postMessage({ type: "resume" });
      engine.current.forceRunning = true; setLayout("force"); setRunning(true); setError("");
    } catch { if (engine.current) engine.current.forceRunning = false; setRunning(false); setError("This browser cannot start the force worker. The saved Atlas layout remains available."); }
  }
  function pause() { workerRef.current?.worker.postMessage({ type: "pause" }); if (engine.current) engine.current.forceRunning = false; setRunning(false); }
  function saveImage() {
    requestAnimationFrame(() => {
      const api = graphRef.current, renderer = api.renderer();
      renderer.render(api.scene(), api.camera());
      renderer.domElement.toBlob(blob => {
      if (!blob) { setError("The graph image could not be saved."); return; }
      const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href = url; a.download = "Surbhandar_full_graph.png"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      });
    });
  }
  const label = labels[hovered ?? selected];
  const nearest = selected === null ? [] : [selected, ...adjacency[selected]];
  return <section className="force-atlas" ref={wrapper} data-force-theme={theme} aria-label="Full-corpus recording graph" data-reviewed-rows>
    <style>{styles}</style>
    <div className="force-atlas-tools" role="group" aria-label="Graph controls">
      <div className="force-atlas-layout" role="group" aria-label="Graph layout">
        <button type="button" aria-label="Atlas layout" aria-pressed={layout === "atlas"} onClick={atlasLayout}>Atlas</button>
        <button type="button" aria-label="Force layout" aria-pressed={layout === "force"} onClick={forceLayout} disabled={running}>Force</button>
      </div>
      {layout === "force" && <button type="button" onClick={running ? pause : forceLayout}>{running ? "Pause motion" : "Resume motion"}</button>}
      <span className="force-atlas-spacer" />
      <button type="button" aria-label="Fit whole graph" onClick={() => fit()}>Fit all</button>
      <button type="button" aria-label="Random song" onClick={() => callback.current?.(Math.floor(Math.random() * positions.length))}>Surprise me</button>
      <details className="force-atlas-options"><summary>View options</summary><div className="force-atlas-options-panel">
        <label>Pitch-black background <input type="checkbox" role="switch" checked={blackBackground} onChange={event => setBlackBackground(event.target.checked)} /></label>
        <label>Connections <select aria-label="Connection display" value={links} onChange={event => setLinks(event.target.value)}>
          <option value="all">All connections</option><option value="selected">Selected song</option><option value="hidden">Hidden</option>
        </select></label>
        <label>Line opacity <input aria-label="Line opacity" type="range" min="0.005" max="0.2" step="0.005" value={opacity} onChange={event => setOpacity(Number(event.target.value))} /></label>
        <label>Dot size <input aria-label="Dot size" type="range" min="1" max="7" step="0.5" value={pointSize} onChange={event => setPointSize(Number(event.target.value))} /></label>
        <label>Image quality <select aria-label="Image quality" value={quality} onChange={event => setQuality(event.target.value)}>
          <option value="auto">Automatic</option><option value="smooth">Smoother motion</option><option value="sharp">Sharper image</option>
        </select></label>
        <div className="force-atlas-option-actions">
          <button type="button" onClick={() => fit(nearest)} disabled={selected === null}>Fit neighbours</button>
          <button type="button" onClick={() => fit(matches)} disabled={!matches.length}>Fit matches</button>
          <button type="button" aria-pressed={rotate} onClick={() => setRotate(!rotate)}>Auto orbit</button>
          <button type="button" onClick={saveImage}>Save image</button>
        </div>
        <p>{rendered.points.toLocaleString()} nodes rendered. {rendered.links.toLocaleString()} background links drawn of {(graph.endpoints.length / 2).toLocaleString()} loaded. Image quality changes resolution, not corpus coverage.</p>
      </div></details>
      <button type="button" onClick={() => {
        const action = document.fullscreenElement ? document.exitFullscreen() : wrapper.current.requestFullscreen();
        action?.catch(() => setError("Fullscreen is unavailable in this browser panel."));
      }}>Fullscreen</button>
    </div>
    <div className="force-atlas-viewport" ref={viewport} style={{ background: backgroundColor }} role="img" aria-label={`${positions.length.toLocaleString()} recordings and ${(graph.endpoints.length / 2).toLocaleString()} directed neighbour connections. Search and buttons provide keyboard access.`}>
      <ForceGraph3D ref={graphRef} graphData={rendererGraph} width={size.width} height={size.height}
        nodeVisibility={false} linkVisibility={false} enablePointerInteraction={false} enableNodeDrag={false}
        showNavInfo={false} cooldownTicks={0} controlType="orbit" rendererConfig={rendererConfig}
        backgroundColor={backgroundColor} />
      {(hovered !== null || selected !== null) && <div className="force-atlas-tooltip">{label ? <><strong>{label.title}</strong>{label.artist && <div>{label.artist}</div>}</> : "Click to explore this recording"}</div>}
    </div>
    <div className="force-atlas-status">
      <span>{graph.nodes.length.toLocaleString()} recordings</span>
      <span>{layout === "atlas" ? "Atlas positions" : `Force layout ${running ? "running" : "paused"} · step ${step}`}</span>
      <output aria-label="Render frame rate">{rendered.fps} fps</output>
    </div>
    {layout === "force" && <p className="force-atlas-motion-note">The connections arrange the map. Your ranked neighbours stay the same.</p>}
    {error && <p role="alert" className="force-atlas-error">{error}</p>}
  </section>;
}
