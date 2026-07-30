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
Checks that the analysis callbacks actually require a login.

display_page() in index.py chooses which layout to render, which is easy to
mistake for access control. It isn't: Dash callbacks are ordinary POSTs to
/_dash-update-component and every analysis callback is registered globally at
import time, so without an explicit guard they can be invoked directly by
anyone who knows the component IDs - and those IDs are readable in the client
bundle. Run: python test_auth_required.py
"""
from index import server


def _post(client, output, inputs=None, state=None):
    body = {
        'output': output,
        'inputs': inputs or [],
        'changedPropIds': [],
    }
    if state is not None:
        body['state'] = state
    return client.post('/_dash-update-component', json=body)


def test_analysis_callback_rejected_when_logged_out():
    """The expensive callbacks must not run for an anonymous caller."""
    client = server.test_client()

    protected = [
        'progress-output.children',       # historical connectivity analysis
        'user-apk-upload-store.data',     # accepts uploaded files
        'precomputed-graph.figure',       # precomputed data access
    ]
    for output in protected:
        resp = _post(client, output)
        assert resp.status_code == 401, (
            f"{output} answered {resp.status_code} to an unauthenticated POST; "
            "expected 401"
        )


def test_login_and_router_still_reachable_when_logged_out():
    """The guard must not lock out the login form itself.

    Without this, the fix would be a lockout rather than a fix: the router
    renders the login page and the login callback checks the credentials, so
    both have to stay callable while nobody is authenticated yet.

    We assert only that the guard does not return 401 for these two. Dash may
    still reject the hand-built request body for its own reasons - these tests
    construct the POST directly rather than going through a browser - but
    anything other than 401 proves the request got past the guard, which is the
    property under test.
    """
    client = server.test_client()

    router = _post(client, 'page-content.children', inputs=[
        {'id': 'url', 'property': 'pathname', 'value': '/'},
    ])
    assert router.status_code != 401, \
        "router callback was blocked; the login page would never render"

    login = _post(
        client,
        '..url.pathname...login-error.children..',
        inputs=[{'id': 'login-button', 'property': 'n_clicks', 'value': 1}],
        state=[
            {'id': 'username-input', 'property': 'value', 'value': 'wrong'},
            {'id': 'password-input', 'property': 'value', 'value': 'wrong'},
        ],
    )
    assert login.status_code != 401, \
        "login callback was blocked; nobody could ever log in"


def test_admin_status_requires_login():
    client = server.test_client()
    resp = client.get('/admin/status')
    assert resp.status_code != 200, \
        "/admin/status served session information to an anonymous caller"


def demo():
    test_analysis_callback_rejected_when_logged_out()
    test_login_and_router_still_reachable_when_logged_out()
    test_admin_status_requires_login()
    print("OK: analysis callbacks require login; login page still reachable")


if __name__ == "__main__":
    demo()
