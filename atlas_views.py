"""CPU generation of Atlas views from private, independently normalized blocks."""

import os
import time
from pathlib import Path


def require_cloud():
    if not (Path('/kaggle/working').is_dir() or Path('/content').is_dir()
            or Path('/mount/src').is_dir() or os.environ.get('DEEPNOTE_PROJECT_ID')):
        raise RuntimeError('Representation computation requires a private cloud runtime')


def generate_view(blocks, selected, point_ids, *, allow_local=False):
    if not allow_local:
        require_cloud()
    import numpy as np
    from threadpoolctl import threadpool_limits

    started = time.perf_counter()
    names = tuple(sorted(selected))
    if not names or len(set(names)) != len(names) or any(name not in blocks for name in names):
        raise ValueError('Choose distinct available representations')
    if len(point_ids) < 31 or len(set(point_ids)) != len(point_ids):
        raise ValueError('A view needs distinct recording identifiers')
    pieces = [np.asarray(blocks[name], dtype=np.float32) for name in names]
    if any(piece.shape != (len(point_ids), 32) or not np.isfinite(piece).all()
           or not np.allclose(np.linalg.norm(piece, axis=1), 1, atol=3e-6) for piece in pieces):
        raise ValueError('Prepared representation shape or normalization is invalid')
    values = np.concatenate(pieces, axis=1)
    values /= np.linalg.norm(values, axis=1, keepdims=True)
    indices = np.empty((len(values), 30), dtype=np.int32)
    distances = np.empty((len(values), 30), dtype=np.float32)
    with threadpool_limits(limits=2):
        # Bounded dot products avoid a full corpus-sized square matrix in the app.
        for offset in range(0, len(values), 64):
            scores = values[offset:offset + 64] @ values.T
            for local, row in enumerate(scores):
                index = offset + local
                row[index] = -np.inf
                nearest = np.argpartition(-row, 29)[:30]
                nearest = nearest[np.lexsort((nearest, -row[nearest]))]
                indices[index] = nearest
                distances[index] = np.clip(1 - row[nearest], 0, 2)
    neighbor_seconds = time.perf_counter() - started
    import umap

    self_ids = np.arange(len(values), dtype=np.int32)[:, None]
    knn_ids = np.concatenate([self_ids, indices[:, :29]], axis=1)
    knn_distances = np.concatenate([np.zeros((len(values), 1), dtype=np.float32), distances[:, :29]], axis=1)
    projector = umap.UMAP(n_components=3, metric='cosine', n_neighbors=30,
                          min_dist=0.1, random_state=42, transform_seed=42,
                          precomputed_knn=(knn_ids, knn_distances, None), n_jobs=1)
    with threadpool_limits(limits=2):
        positions = projector.fit_transform(values).astype(np.float32)
    if positions.shape != (len(values), 3) or not np.isfinite(positions).all():
        raise ValueError('Projection did not produce a complete finite map')
    return {'point_ids': list(point_ids), 'positions': positions.tolist(),
            'adjacency': indices[:, :25].tolist(), 'representations': list(names),
            'point_count': len(values), 'projection': 'UMAP',
            'neighbor_metric': 'cosine on equally balanced prepared blocks',
            'neighbor_seconds': neighbor_seconds,
            'elapsed_seconds': time.perf_counter() - started}


def validate_view(view, catalogue_size=10819):
    import math

    identifiers = view['point_ids']
    count = view['point_count']
    if (count != len(identifiers) or count < 31 or len(set(identifiers)) != count
            or any(type(index) is not int or not 0 <= index < catalogue_size for index in identifiers)
            or len(view['positions']) != count or len(view['adjacency']) != count):
        raise ValueError('Map coverage is invalid')
    for index, (position, neighbors) in enumerate(zip(view['positions'], view['adjacency'], strict=True)):
        if (len(position) != 3 or not all(type(value) in (float, int) and math.isfinite(value) for value in position)
                or len(neighbors) != 25 or len(set(neighbors)) != 25 or index in neighbors
                or any(type(other) is not int or not 0 <= other < count for other in neighbors)):
            raise ValueError('Map coordinates or neighbours are invalid')
    return view


def apply_view(rows, view):
    validate_view(view, len(rows))
    identifiers = view['point_ids']
    return [{**rows[original], 'position': position, 'neighbors': neighbors}
            for original, position, neighbors in zip(identifiers, view['positions'], view['adjacency'], strict=True)]
