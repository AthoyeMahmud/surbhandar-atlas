export default function ({ parentElement, data, setTriggerValue }) {
  const graph = parentElement.querySelector('.atlas-map');
  const selected = data.selected;
  const neighbors = new Set(data.neighbors);
  const matches = new Set(data.matches);
  const focused = selected !== null;
  const palette = ['#638dff', '#32cfb5', '#ffa66b'];
  const escape = text => String(text).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const hover = index => {
    const label = data.labels[index];
    return label ? `${escape(label.title)}<br>${escape(label.artist)}` : 'Click to explore this recording';
  };
  const points = data.positions;
  const all = points.map((_, i) => i);
  const trace = (ids, marker, opacity = 1) => ({
    type: 'scatter3d', mode: 'markers',
    x: ids.map(i => points[i][0]), y: ids.map(i => points[i][1]), z: ids.map(i => points[i][2]),
    customdata: ids, text: ids.map(hover), hovertemplate: '%{text}<extra></extra>',
    marker: { ...marker, opacity }, showlegend: false,
  });
  const traces = [trace(all, {
    size: 2.6,
    color: all.map(i => focused ? '#233b4e' : matches.size && !matches.has(i) ? '#233b4e' : palette[data.bands[i]]),
  }, focused || matches.size ? 0.38 : 0.78)];
  if (matches.size) traces.push(trace([...matches], { size: 4, color: '#72e6ff' }));
  if (neighbors.size) traces.push(trace([...neighbors], { size: 6, color: '#ff74b6', line: { color: '#ffd5e8', width: 1 } }));
  if (selected !== null) traces.push(trace([selected], { size: 9, color: '#ffda85', line: { color: '#fff5d8', width: 2 } }));
  const focusIds = data.focused && selected !== null ? [selected, ...neighbors] : all;
  const axes = ['x', 'y', 'z'];
  const scene = { aspectmode: 'cube', dragmode: 'orbit' };
  axes.forEach((axis, dimension) => {
    const values = focusIds.map(i => points[i][dimension]);
    const min = Math.min(...values), max = Math.max(...values);
    const pad = Math.max((max - min) * 0.18, 0.6);
    scene[axis + 'axis'] = { visible: false, range: [min - pad, max + pad] };
  });
  // ponytail: one chart per session; retain camera on ordinary reruns, reset when focus mode changes.
  const layout = {
    autosize: true, paper_bgcolor: '#0c1929', plot_bgcolor: '#0c1929',
    font: { color: '#ecf5ff', family: 'sans-serif' },
    margin: { l: 0, r: 0, t: 0, b: 0 },
    scene, uirevision: data.focused ? `focus-${selected}-${data.revision}` : `collection-${data.revision}`,
    hoverlabel: { bgcolor: '#122c40', bordercolor: '#32cfb5', font: { color: '#fff' } },
  };
  Plotly.react(graph, traces, layout, { responsive: true, displayModeBar: false, scrollZoom: true, displaylogo: false })
    .then(() => {
      graph.removeAllListeners('plotly_click');
      graph.on('plotly_click', event => {
        const index = event.points[0]?.customdata;
        if (Number.isInteger(index)) setTriggerValue('picked', index);
      });
    }).catch(() => {
      graph.textContent = 'The 3D map needs WebGL. You can still search and explore tracks alongside it.';
    });
  const observer = new ResizeObserver(() => Plotly.Plots.resize(graph));
  observer.observe(graph);
  return () => observer.disconnect();
}
