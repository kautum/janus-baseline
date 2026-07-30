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
Checks the session bookkeeping in utils/concurrency_manager.py is thread-safe.

This matters because the server runs threaded, clean_stale_sessions() is called
on *every* request, and analyses register/remove sessions from their own threads
hours apart. Unsynchronised, one thread iterating active_sessions while another
inserts raises "dictionary changed size during iteration" - and because the
iteration happens in the page-routing path, that breaks the site for every user,
not only the one running an analysis.

Removing the lock from concurrency_manager makes test_no_race_between_register_and_clean
fail. Run: python test_concurrency.py
"""
import threading
import time

from utils import concurrency_manager as cm

WORKERS = 8
ITERATIONS = 300


def _reset():
    cm.active_sessions.clear()


def test_no_race_between_register_and_clean():
    """Hammer register/remove against the cleaner and require zero exceptions."""
    _reset()
    errors = []
    stop = threading.Event()

    def churn(worker_id):
        try:
            for i in range(ITERATIONS):
                session_id = f"w{worker_id}-{i}"
                cm.register_session(session_id, {'num_apks': 1})
                cm.has_capacity()
                cm.remove_session(session_id)
        except Exception as e:                      # noqa: BLE001 - recording it is the point
            errors.append(f"churn worker {worker_id}: {type(e).__name__}: {e}")

    def clean():
        try:
            while not stop.is_set():
                cm.clean_stale_sessions()
        except Exception as e:                      # noqa: BLE001
            errors.append(f"cleaner: {type(e).__name__}: {e}")

    cleaner = threading.Thread(target=clean, daemon=True)
    cleaner.start()

    workers = [threading.Thread(target=churn, args=(n,)) for n in range(WORKERS)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()

    stop.set()
    cleaner.join(timeout=5)

    assert not errors, "concurrent access raised:\n  " + "\n  ".join(errors)
    assert not cm.active_sessions, \
        f"sessions leaked after every register was matched by a remove: {cm.active_sessions}"


def test_stale_sessions_are_removed():
    """A session older than SESSION_TIMEOUT is cleaned up; a fresh one is not."""
    _reset()
    cm.register_session('fresh', {'num_apks': 1})
    cm.register_session('stale', {'num_apks': 1})
    # Backdate one past the timeout rather than waiting half an hour.
    cm.active_sessions['stale']['start_time'] = time.time() - (cm.SESSION_TIMEOUT + 60)

    cm.clean_stale_sessions()

    assert 'stale' not in cm.active_sessions, "stale session was not cleaned up"
    assert 'fresh' in cm.active_sessions, "a live session was wrongly cleaned up"
    _reset()


def test_capacity_gate():
    """has_capacity() must stop admitting work at the configured limit."""
    _reset()
    for i in range(cm.MAX_CONCURRENT_USERS):
        assert cm.has_capacity(), \
            f"refused work at {i} sessions, below the limit of {cm.MAX_CONCURRENT_USERS}"
        cm.register_session(f"s{i}", {'num_apks': 1})

    assert not cm.has_capacity(), \
        f"admitted work beyond the limit of {cm.MAX_CONCURRENT_USERS}"

    cm.remove_session('s0')
    assert cm.has_capacity(), "did not free a slot after a session finished"
    _reset()


def test_remove_unknown_session_is_harmless():
    _reset()
    assert cm.remove_session('never-existed') is False


def demo():
    test_no_race_between_register_and_clean()
    test_stale_sessions_are_removed()
    test_capacity_gate()
    test_remove_unknown_session_is_harmless()
    print(f"OK: {WORKERS} threads x {ITERATIONS} register/remove cycles against a "
          "concurrent cleaner, no races; stale cleanup and capacity gate correct")


if __name__ == "__main__":
    demo()
