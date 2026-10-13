"""Load checksum-pinned representation blocks into the private cloud server."""

import base64
import configparser
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path

from atlas_views import require_cloud


@lru_cache(maxsize=1)
def rclone_executable():
    require_cloud()
    request = urllib.request.Request('https://api.github.com/repos/rclone/rclone/releases/latest',
                                     headers={'User-Agent': 'Surbhandar-private-cloud'})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    version = release['tag_name']
    if not re.fullmatch(r'v\d+\.\d+\.\d+', version):
        raise RuntimeError('Provider client release is invalid')
    existing = shutil.which('rclone')
    if existing and subprocess.check_output([existing, 'version'], text=True).splitlines()[0] == 'rclone ' + version:
        return existing
    target = Path(tempfile.gettempdir()) / ('atlas-rclone-' + version)
    if not target.exists():
        asset = next(item for item in release['assets'] if item['name'] == f'rclone-{version}-linux-amd64.zip')
        with urllib.request.urlopen(asset['browser_download_url'], timeout=60) as response:
            archive = response.read()
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            name = next(name for name in package.namelist() if name.endswith('/rclone'))
            target.write_bytes(package.read(name))
        target.chmod(0o700)
    if subprocess.check_output([str(target), 'version'], text=True).splitlines()[0] != 'rclone ' + version:
        raise RuntimeError('Provider client version check failed')
    return str(target)


def load_private_blocks(config_b64, remote, manifest_sha256):
    require_cloud()
    import numpy as np

    if not re.fullmatch(r'[0-9a-f]{64}', manifest_sha256):
        raise ValueError('Prepared manifest checksum is invalid')
    executable = rclone_executable()
    config = configparser.ConfigParser(interpolation=None)
    raw = base64.b64decode(config_b64, validate=True)
    config.read_string(raw.decode())
    if len(config.sections()) != 1 or remote.split(':', 1)[0] != config.sections()[0]:
        raise ValueError('Private storage configuration is invalid')
    with tempfile.TemporaryDirectory(prefix='atlas-private-', dir='/tmp') as temporary:
        folder = Path(temporary)
        secret = folder / 'rclone.conf'
        secret.write_bytes(raw)
        secret.chmod(0o600)
        environment = {**os.environ, 'RCLONE_CONFIG': str(secret)}

        def transfer(arguments):
            result = subprocess.run([executable, *arguments, '--tpslimit', '8', '--retries', '2',
                                     '--contimeout', '20s', '--timeout', '1m'], env=environment,
                                    capture_output=True, timeout=180)
            if result.returncode:
                raise RuntimeError('Private representation storage is currently unavailable')

        manifest_path = folder / 'manifest.json'
        transfer(['copyto', remote.rstrip('/') + '/manifest.json', str(manifest_path)])
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != manifest_sha256:
            raise ValueError('Prepared manifest checksum failed')
        manifest = json.loads(manifest_path.read_text())
        if (not manifest['complete'] or manifest['point_count'] != 10819
                or manifest['eligible_point_count'] != 10817 or len(manifest['hiatus_point_ids']) != 2):
            raise ValueError('Prepared representation coverage is invalid')
        files = []
        for name, block in manifest['blocks'].items():
            if (not re.fullmatch(r'[a-z0-9-]+', name) or block['file'] != name + '.npy'
                    or block['dimensions'] != 32 or block['rows'] not in (10817, 10819)
                    or len(block['point_ids']) != block['rows']
                    or len(set(block['point_ids'])) != block['rows']
                    or any(type(index) is not int or not 0 <= index < 10819 for index in block['point_ids'])):
                raise ValueError('Prepared block manifest is invalid')
            files.append(block['file'])
        selected = folder / 'files.txt'
        selected.write_text('\n'.join(files) + '\n')
        transfer(['copy', remote, str(folder), '--files-from', str(selected), '--transfers', '4'])
        arrays = {}
        for name, block in manifest['blocks'].items():
            path = folder / block['file']
            if hashlib.sha256(path.read_bytes()).hexdigest() != block['sha256']:
                raise ValueError('Prepared representation checksum failed')
            array = np.load(path, allow_pickle=False)
            if (array.shape != (block['rows'], 32) or not np.isfinite(array).all()
                    or not np.allclose(np.linalg.norm(array, axis=1), 1, atol=3e-6)):
                raise ValueError('Prepared representation validation failed')
            arrays[name] = array
        return manifest, arrays
