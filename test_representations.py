"""Cloud checks for map coverage, identity, neighbour switching and failure boundaries."""

import gzip
import json
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

from atlas import load_catalogue
from atlas_views import apply_view, generate_view, require_cloud, validate_view


def check():
    require_cloud()
    root = Path(__file__).parent
    rows, _ = load_catalogue()
    manifest = json.loads((root / 'data/views/manifest.json').read_text())
    views = {}
    for entry in manifest['views']:
        with gzip.open(root / 'data/views' / entry['file'], 'rt') as file:
            view = validate_view(json.load(file))
        assert view['point_count'] == (10819 if entry['key'] == 'mert-clap' else 10817)
        views[entry['key']] = view
        combined = apply_view(rows, view)
        assert all(row['title'] == rows[original]['title'] and row['aliases'] == rows[original]['aliases']
                   for row, original in zip(combined, view['point_ids'], strict=True))
        assert combined[0]['neighbors'] == view['adjacency'][0]
    assert len(views) == 8
    for key in ('mert-muq', 'clap-muq'):
        assert views[key]['representations'] == sorted(key.split('-'))
    rhythm = views['rhythm']
    sample = rhythm['point_ids'][100]
    original_position = list(rows[sample]['position'])
    original_neighbors = list(rows[sample]['neighbors'])
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=60).run()
    assert not app.exception, [error.message for error in app.exception]
    app.session_state.selected = sample
    app.text_input[0].set_value(rows[sample]['title']).run()
    query = app.session_state.query
    app.selectbox(key='representation_view').set_value('rhythm').run()
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state.selected == sample and app.session_state.query == query
    active_index = rhythm['point_ids'].index(sample)
    app.radio(key='explorer_panel').set_value('Song').run()
    actual = [int(button.key.removeprefix('neighbor_')) for button in app.button
              if (button.key or '').startswith('neighbor_')]
    assert actual == rhythm['adjacency'][active_index]
    app.selectbox(key='representation_view').set_value('original').run()
    assert not app.exception and app.session_state.selected == sample and app.session_state.query == query
    assert [int(button.key.removeprefix('neighbor_')) for button in app.button
            if (button.key or '').startswith('neighbor_')] == original_neighbors
    assert rows[sample]['position'] == original_position and rows[sample]['neighbors'] == original_neighbors
    for key in ('mert-muq', 'clap-muq'):
        app.selectbox(key='representation_view').set_value(key).run()
        assert not app.exception and app.session_state.selected == sample and app.session_state.query == query
        index = views[key]['point_ids'].index(sample)
        assert [int(button.key.removeprefix('neighbor_')) for button in app.button
                if (button.key or '').startswith('neighbor_')] == views[key]['adjacency'][index]
    available = set(rhythm['point_ids'])
    held = next(index for index in range(10819) if index not in available)
    app.session_state.selected = held
    app.selectbox(key='representation_view').set_value('rhythm').run()
    assert not app.exception and app.session_state.selected == held
    assert any('unavailable in this map' in message.value for message in app.info)
    app.selectbox(key='representation_view').set_value('original').run()
    assert not app.exception and app.session_state.selected == held

    malformed = {**rhythm, 'point_ids': [rhythm['point_ids'][0]] * len(rhythm['point_ids'])}
    try:
        validate_view(malformed)
        raise AssertionError('Duplicate identities were accepted')
    except ValueError:
        pass
    # Synthetic fixtures check rejection only; they do not establish corpus results.
    values = np.ones((40, 32), dtype=np.float32)
    for selected in ([], ['missing'], ['test', 'test'], ['test']):
        try:
            generate_view({'test': values}, selected, list(range(40)))
            raise AssertionError('Invalid selection or block normalization was accepted')
        except ValueError:
            pass
    print('PASS: full view coverage, identity and selection preservation, ranked neighbour switching, hiatus visibility, invalid input rejection')


if __name__ == '__main__':
    check()
