# Surbhandar · Music Atlas

**[Launch the Atlas](https://surbhandar-atlas.streamlit.app/)**

Public preview of an ongoing project. Not currently released under an
open-source license. Original project materials are © 2026 Athoye Mahmud,
all rights reserved; see [LICENSE.md](LICENSE.md). Third-party components retain
their respective licenses.

A small Streamlit app for exploring 10,819 Bangla recordings. Search by song,
artist, album, or an original filename. Click a point or a search result to see
its 25 nearest tracks, then follow any neighbour to continue exploring.

The React force graph loads all 10,819 nodes and 270,475 directed connections.
Start with the saved Atlas positions, or run the full force layout in a
background worker. Controls cover pause/resume, orbit/pan/zoom, whole-graph,
search and neighbour framing, connection visibility, line opacity, dot size,
auto orbit, fullscreen, and PNG export. Force positions are temporary display
positions; the original ranked neighbour lists stay authoritative.

The new graph is the default. A small **Graph** control below the map lets you
choose **Previous graph**, retaining the earlier Plotly view. Switching keeps
your search, selected song, and neighbours; both render the currently selected representation map.
Plotly is loaded only when the previous graph is selected.

## Representations

The visible **Representations** picker above the graph selects Original Atlas
or one of eight prepared maps: rhythm, tonal movement, MuQ, rhythm plus tonal
movement, MERT plus CLAP, MERT plus MuQ, CLAP plus MuQ, or all six primary
representations. Original Atlas retains all 10,819 recordings and its
accepted 96D geometry. Maps using the new extraction include 10,817 recordings;
two unresolved source recordings remain on hiatus and are never imputed.
MERT plus CLAP has all 10,819. Song selection and search survive switching.

Prepared views contain only display coordinates, opaque point indices and
ordered neighbour indices. Each selected representation contributes a
separately normalized 32D block. Cosine similarity in the combined feature
space determines neighbours; the 3D projection supplies display positions.
Choosing several layers gives each chosen layer its own contribution.

The current implementation is for localhost review; these changes have not
been pushed or deployed to the public app. The main repository's cloud-built
preview is available at `http://localhost:4193/?view=1&tab=atlas`.

Optional custom combinations require a cloud CPU server. They need three
server secrets: `LOSSLESS_RCLONE_CONFIG_B64` (one private Drive remote),
`ATLAS_PREPARED_REMOTE` (the prepared-block folder), and
`ATLAS_PREPARED_MANIFEST_SHA256` (the verified manifest pin). Keep these outside
Git. The server checks the current stable rclone release, verifies the pinned
manifest and all 32D blocks, then retains the blocks in a server resource cache.
Only the resulting map and neighbour indices reach the browser. Generation is
serialized, and at most three completed combinations are cached. The prepared
maps work without these secrets or any connected notebook/GPU.

The private Kaggle CPU check used two cores: generation including block
selection took 24.9 seconds cold, then 6.8–9.4 seconds warm, with peak RSS
of 651 MiB. It exercised all 36 blocks and selected layers, plus two actual
generations through the Streamlit controls. Hosted Streamlit latency remains
unmeasured; the custom backend has not been configured in the public app.
The two added maps were generated locally from private reduced blocks with
the same numerical versions: 32.3 seconds for MERT plus MuQ and 13.9 seconds
for CLAP plus MuQ, or 53.6 seconds including quality checks. Tests and builds
were kept in private cloud compute.

## Run in a private cloud runtime

Extraction, tests and builds run in private cloud environments. The owner
authorized local combo-map generation from private prepared blocks on
9 October 2026. Ordinary local display of an already built app is permitted.
Use Python 3.12 or
newer in the cloud:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

For Streamlit Community Cloud, select this repository, `main`, and `app.py`.
Make the **app** public if it should open without login. Repository visibility
is managed separately; public visibility does not grant an open-source license.
Do not enable static serving for the `data` directory.

## Sharing boundary

This repository starts fresh and contains only the browsing application and a
reduced, reviewed catalogue. It contains no source audio, extraction pipeline,
raw features, embeddings, private cloud paths, credentials, recording hashes, or
source channel identifiers. Optional custom generation loads verified reduced
blocks from private storage into the cloud server; they remain outside Git and
the browser payload. Original filenames are used as server-side search aliases
in the app; they are also readable in the catalogue when the repository is public.

The server holds the complete catalogue. The map receives all coordinates,
colour bands, opaque numeric point IDs, and the complete ordered numeric
neighbour table so it can draw every connection. Names are sent for the current
selection and its 25 neighbours; search-result names appear in the native UI.
These browser payload limits do not restrict access to files in a public
repository. A public repository exposes its checked-in source, complete reduced
catalogue, prepared maps, and published Git history to viewers.

This is disclosure reduction, not copy prevention. Full geometry and neighbour
topology can be captured; repeated browsing can collect more names.
The no-login app has no restriction on who can view it once its URL is shared.
This app's neighbour lists preserve the original ranks and are not calculated
from distances on the 3D screen.

## Check

```sh
.venv/bin/python test_atlas.py
.venv/bin/python test_representations.py
```

The cloud checks validate every recording and neighbourhood, multilingual search,
the browser payload boundary, graph and representation switching, deferred-source
visibility, and the native Streamlit controls.

The deployed app uses the checked-in `map.js` and `legacy-map.js`; it needs no Node installation.
`frontend/map.jsx` is the Streamlit bridge. The shared graph renderer and build
are maintained in the main repository. To regenerate both bundles in the cloud:

```sh
cd /path/to/private-cloud-checkout/scripts/atlas-graph
npm ci --ignore-scripts
node build.mjs /path/to/private-cloud-sharing-app
```

Dependency versions are pinned in that directory's lockfile. Vendored notices
are included in `frontend/force-graph.LICENSE.txt`.

## Design references

- [Streamlit layouts and containers](https://docs.streamlit.io/develop/concepts/design/layouts-and-containers)
- [Designing Streamlit apps for users](https://blog.streamlit.io/designing-streamlit-apps-for-the-user-part-ii/)
- [Native bidirectional components](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component)
