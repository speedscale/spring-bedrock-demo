#!/usr/bin/env python3
"""Copy reviewed Markdown RRPairs into a new candidate without changing inputs."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def pairs(root):
    found = []
    for source in sorted(root.glob('*/*.md')):
        if source.parent.name.startswith('.'):
            continue
        if source.is_symlink() or source.parent.is_symlink():
            raise ValueError(f'symlink is not a recording: {source}')
        text = source.read_text()
        match = re.search(r'^json: (.*)$', text, re.M)
        if not match:
            raise ValueError(f'missing RRPair metadata: {source}')
        meta = json.loads(match[1])
        if meta.get('direction') not in ('IN', 'OUT') or not meta.get('uuid'):
            raise ValueError(f'missing direction or UUID: {source}')
        found.append((source, source.relative_to(root), meta['uuid']))
    if not found:
        raise ValueError(f'no Markdown RRPairs in {root}')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('additions', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    inputs = [args.baseline.resolve(), args.additions.resolve()]
    if any(candidate == root or candidate.is_relative_to(root) or root.is_relative_to(candidate) for root in inputs):
        parser.error('candidate must be separate from both inputs')
    if candidate.exists():
        parser.error('candidate already exists; choose a new path')
    paths, uuids, files, manifest = set(), set(), [], []
    try:
        for label, root in zip(('baseline', 'additions'), inputs):
            for source, relative, uuid in pairs(root):
                if relative in paths or uuid in uuids:
                    raise ValueError(f'duplicate path or UUID: {relative}')
                paths.add(relative)
                uuids.add(uuid)
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                files.append((source, relative, digest))
                manifest.append({'source': label, 'file': str(relative), 'uuid': uuid, 'sha256': digest})
    except (OSError, ValueError) as error:
        parser.error(str(error))
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.mkdir()
    try:
        for source, relative, digest in files:
            target = candidate / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError(f'input changed while copying: {source}')
        (candidate / 'provenance.json').write_text(json.dumps({'files': manifest}, indent=2) + '\n')
    except BaseException:
        shutil.rmtree(candidate)
        raise
    print(f'{candidate.name}: {len(files)} pairs copied; input recordings unchanged')


if __name__ == '__main__':
    main()
