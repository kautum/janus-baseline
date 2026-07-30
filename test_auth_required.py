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
/_dash-update-component and every callback is registered globally at import
time, so without an explicit guard they can be invoked directly by anyone who
knows the component IDs - and those IDs are listed by /_dash-dependencies.

Run: python test_auth_required.py
"""
from app import app
from index import PUBLIC_CALLBACK_OUTPUTS, server


def _post(client, output, inputs=None, state=None):
    body = {'output': output, 'inputs': inputs or [], 'changedPropIds': []}
    if state is not None:
        body['state'] = state
    return client.post('/_dash-update-component', json=body)


def _registered_outputs():
    """The output keys Dash actually dispatches on."""
    return set(app.callback_map)


def test_public_outputs_are_real_callbacks():
    """Guard the guard: if a callback is renamed, the allowlist must not
    silently start referring to something that no longer exists."""
    missing = PUBLIC_CALLBACK_OUTPUTS - _registered_outputs()
    assert not missing, (
        f"allowlisted outputs are not registered callbacks: {missing}. "
        "The login page would be unreachable."
    )


def test_every_other_callback_requires_login():
    """Every registered callback except the allowlisted two must return 401.

    Enumerating the real callback map rather than hand-picking a few names
    means a newly added callback is covered automatically - and that this test
    cannot pass by naming outputs that don't exist.
    """
    client = server.test_client()
    protected = _registered_outputs() - PUBLIC_CALLBACK_OUTPUTS
    assert protected, "no protected callbacks found - the test is not testing anything"

    unguarded = [
        output for output in protected
        if _post(client, output).status_code != 401
    ]
    assert not unguarded, (
        f"{len(unguarded)} callback(s) answered an unauthenticated POST without "
        f"401, e.g. {unguarded[:3]}"
    )


def test_login_and_router_stay_reachable():
    """The guard must not lock out the login form itself.

    Asserted as "not 401": these requests are hand-built rather than sent by a
    browser, so Dash may reject the body for its own reasons. Anything other
    than 401 proves the request got past the guard, which is what's under test.
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


def test_malformed_body_is_refused():
    """The guard must fail closed, not open."""
    client = server.test_client()

    for body in (None, {}, {'output': ''}, {'output': 'page-content.children.extra'}):
        resp = client.post('/_dash-update-component', json=body)
        assert resp.status_code == 401, \
            f"malformed body {body!r} was not refused (got {resp.status_code})"

    # A substring of an allowlisted name must not be enough to get through.
    resp = _post(client, '..progress-historical-connectivity.children...login-error.children..')
    assert resp.status_code == 401, \
        "an output merely mentioning an allowlisted name was let through"


def test_admin_status_requires_login():
    client = server.test_client()
    resp = client.get('/admin/status', follow_redirects=False)
    assert resp.status_code in (301, 302, 401, 403), (
        f"/admin/status answered {resp.status_code} to an anonymous caller; "
        "it discloses active session information"
    )


def demo():
    test_public_outputs_are_real_callbacks()
    test_every_other_callback_requires_login()
    test_login_and_router_stay_reachable()
    test_malformed_body_is_refused()
    test_admin_status_requires_login()
    n = len(_registered_outputs() - PUBLIC_CALLBACK_OUTPUTS)
    print(f"OK: all {n} non-public callbacks require login; login page reachable; "
          "guard fails closed")


if __name__ == "__main__":
    demo()
