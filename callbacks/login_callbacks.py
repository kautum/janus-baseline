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
import os
import secrets

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask_login import login_user

VALID_USERNAME = os.environ.get('JANUS_USERNAME', 'admin')

# ponytail: single shared login for a small research tool, no user database.
# Mirrors the SECRET_KEY fallback already used in app.py: if JANUS_PASSWORD
# isn't set, generate one and print it once rather than hardcoding a secret.
# Upgrade to per-user accounts if JANUS gets more than a handful of users.
if 'JANUS_PASSWORD' in os.environ:
    VALID_PASSWORD = os.environ['JANUS_PASSWORD']
else:
    VALID_PASSWORD = secrets.token_urlsafe(12)
    print(f"⚠️  JANUS_PASSWORD not set. Generated one-time login password: {VALID_PASSWORD}")


def register_callbacks(app, User):
    @app.callback(
        [Output('url', 'pathname'),
         Output('login-error', 'children')],
        [Input('login-button', 'n_clicks')],
        [State('username-input', 'value'),
         State('password-input', 'value')],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        # prevent_initial_call isn't enough on its own: the login form is mounted
        # dynamically by the router callback, and Dash fires the callbacks of a
        # newly mounted component regardless. Without this the page greets every
        # visitor with "Invalid username or password" before they've typed
        # anything.
        if not n_clicks:
            raise PreventUpdate

        if username == VALID_USERNAME and password == VALID_PASSWORD:
            login_user(User(username))
            return '/home', ''
        return dash.no_update, 'Invalid username or password'
