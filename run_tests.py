# Copyright 2025 Elisa
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Run every check in one go:  python run_tests.py

Deliberately plain - no pytest, no fixtures, no plugins - so it works in the
same environment that runs the app, with nothing extra to install. Each
test_*.py module exposes a demo() that raises AssertionError on failure.
"""
import importlib
import os
import sqlite3
import sys
import traceback

# Modules importing index.py pull in the callback registry, which reads the
# package index at import time. Provide empty stand-ins if the real data files
# aren't present so the checks can run on a clean clone.
STUB_FILES = {
    'androzoo.db': lambda p: sqlite3.connect(p).close(),
    'filtered_package_ids_with_counts10_ver.json': lambda p: open(p, 'w').write('{}'),
}

TEST_MODULES = [
    'test_upload_safety',
    'test_auth_required',
    'test_concurrency',
]


def _make_stubs():
    """Create missing data files, returning the ones we created so we can tidy up."""
    created = []
    for name, make in STUB_FILES.items():
        if not os.path.exists(name):
            make(name)
            created.append(name)
    return created


def main():
    created = _make_stubs()
    failures = []

    try:
        for name in TEST_MODULES:
            try:
                module = importlib.import_module(name)
                module.demo()
                print(f"PASS  {name}")
            except Exception:
                failures.append(name)
                print(f"FAIL  {name}")
                traceback.print_exc()
    finally:
        for name in created:
            try:
                os.remove(name)
            except OSError:
                pass

    print()
    if failures:
        print(f"{len(failures)} of {len(TEST_MODULES)} suites failed: {', '.join(failures)}")
        return 1

    print(f"All {len(TEST_MODULES)} suites passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
