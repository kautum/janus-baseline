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
Central tunable settings for Janus. A prior version of this file was deleted
from the repo, leaving `historical_connectivity_logic.py` and
`apk_analysis_core.py` importing names that no longer existed anywhere.
This restores just the names those modules reference.
"""
import os

# How long (seconds) a single analysis run is allowed to keep downloading/
# processing APKs before it cuts itself off and returns partial results.
PROCESSING_TIMEOUT = int(os.environ.get('JANUS_PROCESSING_TIMEOUT', 3600))

# Retry policy for AndroZoo APK downloads (see utils/apk_analysis_core.py).
MAX_DOWNLOAD_RETRIES = int(os.environ.get('JANUS_MAX_DOWNLOAD_RETRIES', 20))
DOWNLOAD_RETRY_CYCLES = int(os.environ.get('JANUS_DOWNLOAD_RETRY_CYCLES', 4))


def get_effective_config():
    """Optional runtime overrides for the historical-connectivity UI/analysis.
    Every key defaults to "no override" so behaviour matches having no
    config.py at all, per the ImportError fallbacks already written in
    apk_analysis_core.py.
    """
    return {
        'override_api_key': False,
        'api_key': None,
        'force_parser': None,
        'max_versions': None,
        'force_single_core': False,
        'show_version_control': True,
        'show_parser_selection': True,
        'show_core_control': True,
        'show_api_key_input': True,
    }
