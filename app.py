"""A full-corpus music browser. Research inputs stay outside this application."""

import random
from pathlib import Path

import streamlit as st
from plotly.offline import get_plotlyjs

from atlas import load_catalogue, map_payload, search_catalogue


ROOT = Path(__file__).parent
st.set_page_config(page_title="Surbhandar · Music Atlas", page_icon="✦", layout="wide")
st.html(f"<style>{(ROOT / 'style.css').read_text()}</style>")


@st.cache_resource
def catalogue():
    return load_catalogue()


@st.cache_resource
def map_component():
    return st.components.v2.component(
        "music_atlas", html='<div class="atlas-map" aria-label="Interactive 3D music atlas"></div>',
        js=get_plotlyjs() + "\n" + (ROOT / "map.js").read_text(),
        isolate_styles=False,
    )


try:
    rows, search_index = catalogue()
except (OSError, ValueError, KeyError, TypeError):
    st.error("The music catalogue could not be loaded. Please try again later.")
    st.stop()

st.session_state.setdefault("selected", None)
st.session_state.setdefault("focus", False)
st.session_state.setdefault("view_revision", 0)


def choose(index):
    if type(index) is int and 0 <= index < len(rows):
        st.session_state.selected = index
        st.session_state.query = ""


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


with st.container(key="hero"):
    st.caption("সুরভাণ্ডার  /  SURBHANDAR")
    st.title("A whole world of Bangla music.")
    st.write("Find a familiar song. Follow its neighbours. Discover your next favourite.")
    st.caption("10,819 recordings  ·  25 neighbours for every song")

with st.container(horizontal=True, vertical_alignment="bottom"):
    query = st.text_input("Search the collection", placeholder="A song, artist, or album…", key="query", width="stretch")
    st.button("Surprise me", icon=":material/shuffle:", on_click=surprise)
    st.button("Reset view", icon=":material/restart_alt:", on_click=clear_selection)

matches = search_catalogue(search_index, query) if query.strip() else []
selected = st.session_state.selected
map_column, explore_column = st.columns([1.85, 1], gap="large")

with map_column:
    with st.container(border=True, key="map_panel"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader("The music atlas")
            st.toggle("Focus on neighbours", key="focus", disabled=selected is None)
        map_component()(
            key="atlas_map", data=map_payload(rows, selected, matches, st.session_state.focus, st.session_state.view_revision),
            on_picked_change=pick_on_map, height="content",
        )
        st.caption("Drag to orbit · scroll to zoom · click a dot to explore")
        st.html('<div class="legend"><span><i class="blue"></i>Darker tone</span><span><i class="teal"></i>Middle</span><span><i class="orange"></i>Brighter tone</span><span><i class="pink"></i>Neighbours</span><span><i class="gold"></i>Selected</span></div>')
    st.caption("Map distances are approximate. The neighbour list is the guide.")

with explore_column:
    if query.strip():
        with st.container(border=True, height=320):
            st.subheader("Search results")
            if not matches:
                st.info("No matches yet. Try a shorter title, artist, or album name.")
            else:
                st.caption(f"{len(matches):,} matches" + (" · showing the first 50; refine your search for more" if len(matches) > 50 else ""))
                for index in matches[:50]:
                    row = rows[index]
                    st.button(f"{row['title']} · {row['artist'] or 'Artist unknown'}", key=f"search_{index}",
                              width="stretch", on_click=choose, args=(index,))
    if selected is None:
        with st.container(border=True, key="welcome"):
            st.subheader("Start anywhere.")
            st.write("Search for a song you know, click any point on the map, or let us pick one for you.")
            st.button("Find me a starting point", type="primary", on_click=surprise, width="stretch")
            st.caption("Every dot is a recording. Every song opens another path.")
    else:
        row = rows[selected]
        with st.container(border=True, key="selected_song"):
            st.caption("YOUR STARTING POINT")
            st.subheader(row["title"])
            st.write(row["artist"] or "Artist unknown")
            if row["album"]:
                st.caption(row["album"])
        st.subheader("25 tracks to explore next")
        st.caption("Closest first. Select any track to continue your journey.")
        with st.container(height=480, border=True, key="neighbors"):
            for rank, index in enumerate(row["neighbors"], 1):
                neighbor = rows[index]
                st.button(f"{rank:02d}  {neighbor['title']} · {neighbor['artist'] or 'Artist unknown'}",
                          key=f"neighbor_{index}", width="stretch", on_click=choose, args=(index,))

st.caption("Surbhandar · Music Atlas")
