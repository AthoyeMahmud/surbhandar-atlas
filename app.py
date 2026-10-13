"""A full-corpus music browser. Research inputs stay outside this application."""

import random
import gzip
import json
import hashlib
import threading
from pathlib import Path

import streamlit as st

from atlas import load_catalogue, map_payload, search_catalogue
from atlas_views import apply_view, generate_view, validate_view


ROOT = Path(__file__).parent
st.set_page_config(page_title="Surbhandar · Music Atlas", page_icon="✦", layout="wide")
st.html(f"<style>{(ROOT / 'style.css').read_text()}</style>")


@st.cache_resource
def catalogue():
    return load_catalogue()


VIEW_LABELS = {'original': 'Original Atlas', 'rhythm': 'Rhythm', 'tonal': 'Tonal movement',
               'muq': 'MuQ', 'rhythm-tonal': 'Rhythm + tonal movement',
               'mert-clap': 'MERT + CLAP', 'all-six': 'All six representations',
               'mert-muq': 'MERT + MuQ', 'clap-muq': 'CLAP + MuQ', 'custom': 'Custom combination'}


def custom_available():
    try:
        return all(key in st.secrets for key in ('LOSSLESS_RCLONE_CONFIG_B64', 'ATLAS_PREPARED_REMOTE', 'ATLAS_PREPARED_MANIFEST_SHA256'))
    except FileNotFoundError:
        return False


@st.cache_resource
def private_blocks(manifest_sha256):
    from private_blocks import load_private_blocks
    return load_private_blocks(st.secrets['LOSSLESS_RCLONE_CONFIG_B64'], st.secrets['ATLAS_PREPARED_REMOTE'],
                               manifest_sha256)


@st.cache_resource
def generation_lock():
    return threading.Lock()


@st.cache_data(max_entries=3, show_spinner=False)
def custom_view(names, manifest_sha256):
    with generation_lock():
        manifest, blocks = private_blocks(manifest_sha256)
        ids = sorted(set.intersection(*(set(manifest['blocks'][name]['point_ids']) for name in names)))
        selected = {}
        for name in names:
            indices = {value: index for index, value in enumerate(manifest['blocks'][name]['point_ids'])}
            selected[name] = blocks[name][[indices[value] for value in ids]]
        return validate_view(generate_view(selected, names, ids))


def representation_label(name):
    labels = {'scalar': 'Signal', 'mert': 'MERT', 'clap': 'CLAP', 'mfcc': 'MFCC',
              'chroma': 'Chroma', 'spectral': 'Spectral shape', 'logmel': 'Log-mel'}
    if '-layer-' in name:
        model, layer = name.split('-layer-')
        return f'{model.upper() if model == "mert" else "MuQ"} · layer {layer}'
    return labels.get(name, VIEW_LABELS.get(name, name))


@st.cache_resource
def prepared_views():
    path = ROOT / 'data/views/manifest.json'
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text())
    return {entry['key']: entry for entry in manifest['views']}


@st.cache_resource
def prepared_view(key):
    entry = prepared_views()[key]
    if entry['file'] != key + '.json.gz':
        raise ValueError('Map filename is invalid')
    path = ROOT / 'data/views' / entry['file']
    with path.open('rb') as file:
        if hashlib.file_digest(file, 'sha256').hexdigest() != entry['sha256']:
            raise ValueError('Map checksum is invalid')
    with gzip.open(path, 'rt', encoding='utf-8') as file:
        view = validate_view(json.load(file))
    if view['point_count'] != entry['point_count'] or view['representations'] != entry['representations']:
        raise ValueError('Map differs from its manifest')
    return view


@st.cache_resource
def map_component(javascript, previous=False):
    return st.components.v2.component(
        "music_atlas_previous" if previous else "music_atlas",
        html=f'<div class="atlas-map{" atlas-map-previous" if previous else ""}" aria-label="Interactive 3D music atlas"></div>',
        js=javascript,
        isolate_styles=False,
    )


try:
    all_rows, all_search_index = catalogue()
    available_views = prepared_views()
except (OSError, ValueError, KeyError, TypeError):
    st.error("The music catalogue could not be loaded. Please try again later.")
    st.stop()

st.session_state.setdefault("selected", None)
st.session_state.setdefault("focus", False)
st.session_state.setdefault("view_revision", 0)
st.session_state.setdefault("explorer_panel", "Song")
st.session_state.setdefault("results_page", 0)
st.session_state.setdefault("graph_view", "New graph")
st.session_state.setdefault('representation_view', 'original')
view_key = st.session_state.representation_view
if view_key not in available_views and view_key != 'original' and not (view_key == 'custom' and 'custom_view' in st.session_state):
    view_key = st.session_state.representation_view = 'original'
try:
    active_view = st.session_state.custom_view if view_key == 'custom' else prepared_view(view_key) if view_key != 'original' else None
except (OSError, ValueError, KeyError, TypeError):
    st.warning('The chosen map could not be loaded. Showing Original Atlas.')
    view_key = st.session_state.representation_view = 'original'
    active_view = None
point_ids = active_view['point_ids'] if active_view else list(range(len(all_rows)))
point_index = {original: index for index, original in enumerate(point_ids)}
rows = apply_view(all_rows, active_view) if active_view else all_rows
search_index = [all_search_index[original] for original in point_ids]


def choose(index):
    if type(index) is int and 0 <= index < len(rows):
        st.session_state.selected = point_ids[index]
        st.session_state.query = ""
        st.session_state.explorer_panel = "Song"
        st.session_state.results_page = 0


def pick_on_map():
    choose(st.session_state.get("atlas_map", {}).get("picked"))


def surprise():
    choose(random.randrange(len(rows)))
    st.session_state.focus = True


def clear_selection():
    st.session_state.selected = None
    st.session_state.focus = False
    st.session_state.query = ""
    st.session_state.view_revision += 1
    st.session_state.explorer_panel = "Song"
    st.session_state.results_page = 0


def search_changed():
    st.session_state.explorer_panel = "Results"
    st.session_state.results_page = 0


def change_page(delta):
    st.session_state.results_page += delta


def change_representation():
    st.session_state.view_revision += 1
    st.session_state.results_page = 0


def generate_combination():
    names = st.session_state.custom_representations
    if not names:
        return
    try:
        with st.spinner('Generating your map…'):
            generated = custom_view(tuple(sorted(names)), st.secrets['ATLAS_PREPARED_MANIFEST_SHA256'])
        st.session_state.custom_view = generated
        st.session_state.representation_view = 'custom'
        st.session_state.pop('generation_error', None)
        change_representation()
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError):
        st.session_state.generation_error = True


with st.container(key="hero"):
    st.html('<h1 class="atlas-title"><span lang="bn">সুরভাণ্ডার</span> <span lang="en">Music Atlas</span></h1>')
    st.write("Find a song. Follow its sound.")

with st.container(horizontal=True, vertical_alignment="bottom", key="search_bar"):
    query = st.text_input("Search the collection", placeholder="A song, artist, album, or filename…", key="query",
                          on_change=search_changed, width="stretch")
    st.button("Surprise me", icon=":material/shuffle:", on_click=surprise)
    st.button("Reset view", icon=":material/restart_alt:", on_click=clear_selection)

with st.container(key="representation_picker"):
    options = ['original', *available_views, *(['custom'] if 'custom_view' in st.session_state else [])]
    st.selectbox('Representations', options, format_func=lambda key: VIEW_LABELS[key],
                 key='representation_view', on_change=change_representation, width=360)
    if custom_available() and st.checkbox('Choose your own combination'):
        try:
            with st.spinner('Loading representations…'):
                manifest, _ = private_blocks(st.secrets['ATLAS_PREPARED_MANIFEST_SHA256'])
            with st.form('representation_combination'):
                names = st.multiselect('Representations', list(manifest['blocks']),
                                       default=['mert', 'clap'], format_func=representation_label,
                                       key='custom_representations')
                st.form_submit_button('Generate map', disabled=not names, on_click=generate_combination)
            if st.session_state.get('generation_error'):
                st.error('This combination could not be generated. Prepared maps remain available; please try again later.')
        except (OSError, ValueError, KeyError, RuntimeError, TimeoutError):
            st.error('This combination could not be generated. Prepared maps remain available; please try again later.')

matches = search_catalogue(search_index, query) if query.strip() else []
result_indices = matches if query.strip() else range(len(rows))
selected = point_index.get(st.session_state.selected)
map_column, explore_column = st.columns([2.8, 1], gap="large")

with map_column:
    with st.container(key="map_panel"):
        previous = st.session_state.graph_view == "Previous graph"
        if previous:
            from plotly.offline import get_plotlyjs
            javascript = get_plotlyjs() + "\n" + (ROOT / "legacy-map.js").read_text()
        else:
            javascript = (ROOT / "map.js").read_text()
        map_component(javascript, previous)(
            key="atlas_map", data={**map_payload(rows, selected, matches, st.session_state.focus, st.session_state.view_revision), 'view_key': ':'.join(['custom', *active_view['representations']]) if view_key == 'custom' else view_key},
            on_picked_change=pick_on_map, height="content",
        )
        if previous:
            st.html(f'<div class="atlas-previous-status">{len(rows):,} recordings · Saved Atlas positions</div>')
        with st.container(horizontal=True, horizontal_alignment="right", key="graph_choice"):
            with st.popover("Graph"):
                st.radio("Choose graph", ("New graph", "Previous graph"), key="graph_view")
                st.caption("Same collection and neighbours.")
        st.caption(f"{VIEW_LABELS[view_key]} · {len(rows):,} recordings · 25 neighbours each")
        if active_view:
            st.caption(' + '.join(representation_label(name) for name in active_view['representations']))
        if len(rows) != len(all_rows):
            st.caption('Two recordings await intact source audio for these representations.')
        if st.session_state.selected is not None and selected is None:
            st.info('The selected recording is unavailable in this map. Switch to Original Atlas to return to it.')
        st.caption("Drag to orbit · scroll to zoom · click a point to explore · shift-drag to pan")
        st.html('<div class="legend"><span><i class="gold"></i>Selected</span><span><i class="pink"></i>Nearest 25</span><span><i class="sky"></i>Search matches</span></div><div class="legend">Audio brightness <span><i class="blue"></i>Lower</span><span><i class="teal"></i>Middle</span><span><i class="orange"></i>Higher</span></div>')

with explore_column:
    st.radio("Explorer panel", ("Song", "Results"), horizontal=True, key="explorer_panel", label_visibility="collapsed")
    st.toggle("Frame neighbours", key="focus", disabled=selected is None)
    if st.session_state.explorer_panel == "Results":
        st.caption(f"{len(result_indices):,} " + ("matching songs" if query.strip() else "recordings in the collection"))
        with st.container(height=460, key="results"):
            if not result_indices:
                st.info("No matches yet. Try a shorter title, artist, or album name.")
            else:
                start = st.session_state.results_page * 50
                for index in result_indices[start:start + 50]:
                    row = rows[index]
                    st.button(f"{row['title']} · {row['artist'] or 'Artist unknown'}", key=f"search_{index}",
                              width="stretch", on_click=choose, args=(index,))
        if result_indices:
            page = st.session_state.results_page
            with st.container(horizontal=True, vertical_alignment="center", key="pages"):
                st.button("Previous", disabled=page == 0, on_click=change_page, args=(-1,))
                st.caption(f"{page + 1} / {(len(result_indices) + 49) // 50}")
                st.button("Next", disabled=(page + 1) * 50 >= len(result_indices), on_click=change_page, args=(1,))
    elif selected is None:
        with st.container(key="welcome"):
            st.subheader("Start with a song.")
            st.write("Search for one you know, or choose any point on the map. Its 25 closest recordings open the next path.")
            st.button("Find me a starting point", type="primary", on_click=surprise)
            st.caption("Every recording available in this map is here. The map is yours to explore.")
    else:
        row = rows[selected]
        with st.container(key="selected_song"):
            st.subheader(row["title"])
            st.write(row["artist"] or "Artist unknown")
            if row["album"]:
                st.caption(row["album"])
        st.subheader("25 neighbours")
        st.caption("Closest first. Select a song to keep exploring.")
        with st.container(height=360, key="neighbors"):
            for rank, index in enumerate(row["neighbors"], 1):
                neighbor = rows[index]
                st.button(f"{rank:02d}  {neighbor['title']} · {neighbor['artist'] or 'Artist unknown'}",
                          key=f"neighbor_{index}", width="stretch", on_click=choose, args=(index,))
        st.caption("The ranked list is the guide. Distances on the 3D map are approximate.")

with st.expander("About this Atlas"):
    if active_view:
        st.write(f"This map includes {len(rows):,} recordings. Selected representations each contribute a normalized 32-dimensional block; cosine similarity in their combined space determines the 25 ranked neighbours.")
        trust = active_view.get('trustworthiness', {}).get('at_25')
        if trust is not None:
            st.caption(f'Projection trustworthiness at 25 neighbours: {trust:.3f}. This measures the projection, not classification accuracy.')
    else:
        st.write("All 10,819 recordings are included, with 25 neighbours each. Signal measurements, MERT, and CLAP are balanced into 96 dimensions; cosine similarity in that space determines the ranked list.")
    st.write("Song names and tags help you search; they do not determine the neighbours. Colours show relative audio brightness, not genres. The saved 3D projection and the force layout are two ways to navigate the same collection.")
    st.caption("This sharing app contains reviewed display metadata and the map. The main research app provides recording metadata sources, technical audio details, and the evidence inspector.")
