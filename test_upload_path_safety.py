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
Regression check for the path-traversal fix in
logic/user_apk_analysis_logic.py. Run directly: python test_upload_path_safety.py
"""
import base64
import os
import shutil

from logic.user_apk_analysis_logic import save_uploaded_file_to_server, save_uploaded_files

UPLOAD_DIR = "uploaded_apks"
CONTENT = "data:application/octet-stream;base64," + base64.b64encode(b"not a real apk").decode()


def demo():
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)

    # A crafted filename trying to escape the upload directory must not
    # write outside it (CWE-22 / zip-slip-style path traversal).
    malicious_filename = "../../../tmp/janus_path_traversal_pwned.txt"
    server_path = save_uploaded_file_to_server(CONTENT, malicious_filename)
    real_path = os.path.realpath(server_path)
    upload_dir_real = os.path.realpath(UPLOAD_DIR)
    assert real_path.startswith(upload_dir_real + os.sep), (
        f"path traversal: {real_path} escaped {upload_dir_real}"
    )
    assert not os.path.exists("/tmp/janus_path_traversal_pwned.txt")

    # Same check for the batch upload path used by save_uploaded_files.
    stored_data = [{"content": CONTENT, "filename": "../../evil.apk"}]
    apk_files = save_uploaded_files(stored_data, UPLOAD_DIR)
    _, batch_path = apk_files[0]
    assert os.path.realpath(batch_path).startswith(upload_dir_real + os.sep)

    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    print("OK: path traversal is blocked in both upload functions")


if __name__ == "__main__":
    demo()
