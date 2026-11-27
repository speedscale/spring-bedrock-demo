#!/usr/bin/env python3
"""Check candidate creation preserves inputs and refuses ambiguous merges."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('extend-recording.py')


class ExtendRecordingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base, self.new, self.output = [self.root / p for p in ('base', 'new', 'candidate')]
        self.write_pair(self.base, 'base.md', 'baseline')
        self.write_pair(self.new, 'new.md', 'new')

    def write_pair(self, root, name, uuid):
        path = root / 'localhost' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('json: ' + json.dumps({'direction': 'IN', 'uuid': uuid}) + '\n')
        return path

    def run_helper(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.base), str(self.new), str(self.output)], capture_output=True, text=True)

    def test_preserves_bytes_and_hashes(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.output / 'provenance.json').read_text())['files']
        self.assertEqual(len(manifest), 2)
        for item in manifest:
            source = (self.base if item['source'] == 'baseline' else self.new) / item['file']
            self.assertEqual(source.read_bytes(), (self.output / item['file']).read_bytes())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item['sha256'])

    def test_refuses_duplicate_uuid(self):
        self.write_pair(self.new, 'new.md', 'baseline')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_refuses_duplicate_path(self):
        self.write_pair(self.new, 'base.md', 'other')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_refuses_existing_candidate(self):
        self.output.mkdir()
        marker = self.output / 'reviewed.txt'
        marker.write_text('preserve')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(marker.read_text(), 'preserve')

    def test_refuses_candidate_inside_input(self):
        self.output = self.base / 'candidate'
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_refuses_symlink(self):
        (self.new / 'localhost' / 'link.md').symlink_to(self.base / 'localhost' / 'base.md')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse(self.output.exists())


    def test_refuses_symlinked_host_directory(self):
        (self.new / 'redirected').symlink_to(self.base / 'localhost', target_is_directory=True)
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
