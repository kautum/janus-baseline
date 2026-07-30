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
Checks on the APK upload path in logic/user_apk_analysis_logic.py.

Everything tested here is client-controlled: a Dash callback is just an HTTP
endpoint, so the filename and the file content both come from whoever is
talking to the server. Run: python test_upload_safety.py
"""
import base64
import io
import os
import shutil
import zipfile

from logic.user_apk_analysis_logic import (
    decode_upload,
    save_uploaded_file_to_server,
    save_uploaded_files,
)

UPLOAD_DIR = "uploaded_apks"


def _fake_apk_payload():
    """A minimal but genuine ZIP archive, which is what an APK is."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('AndroidManifest.xml', 'stub')
    return ("data:application/vnd.android.package-archive;base64,"
            + base64.b64encode(buf.getvalue()).decode())


def test_path_traversal_is_blocked():
    """A crafted filename must not escape the upload directory (CWE-22).

    This matters twice over: the stored path is later handed to os.remove()
    when the user removes a file from the list, so escaping the directory
    means arbitrary deletion, not only arbitrary write.
    """
    payload = _fake_apk_payload()
    upload_dir_real = os.path.realpath(UPLOAD_DIR)

    server_path = save_uploaded_file_to_server(payload, "../../../tmp/pwned.apk")
    assert os.path.realpath(server_path).startswith(upload_dir_real + os.sep), \
        f"escaped the upload directory: {server_path}"
    assert not os.path.exists("/tmp/pwned.apk"), "wrote outside the upload directory"

    batch = save_uploaded_files(
        [{"content": payload, "filename": "../../evil.apk"}], UPLOAD_DIR
    )
    _, batch_path = batch[0]
    assert os.path.realpath(batch_path).startswith(upload_dir_real + os.sep)


def test_non_apk_upload_is_rejected():
    """Anything that isn't a ZIP archive must be refused before it reaches disk."""
    not_an_apk = ("data:text/plain;base64,"
                  + base64.b64encode(b"#!/bin/sh\necho not an apk").decode())
    try:
        decode_upload(not_an_apk, "payload.apk")
    except ValueError:
        return
    raise AssertionError("a non-ZIP payload was accepted as an APK")


def test_malformed_payload_is_rejected():
    for bad in ("", "no-comma-here"):
        try:
            decode_upload(bad, "x.apk")
        except ValueError:
            continue
        raise AssertionError(f"malformed payload accepted: {bad!r}")


def demo():
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    try:
        test_path_traversal_is_blocked()
        test_non_apk_upload_is_rejected()
        test_malformed_payload_is_rejected()
    finally:
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    print("OK: path traversal blocked; non-APK and malformed uploads rejected")


if __name__ == "__main__":
    demo()
