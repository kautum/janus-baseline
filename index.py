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
from dash import dcc, html
from dash.dependencies import Input, Output
from app import app, User, server
import dash_bootstrap_components as dbc
from flask import redirect, request
from flask_login import current_user, login_required, logout_user

import layouts.login_layout as login
import layouts.historical_connectivity_layout as historical_connectivity
import layouts.user_apk_analysis_layout as user_apk_analysis
import layouts.precomputed_connectivity_layout as precomputed_connectivity
import layouts.home_layout as home_layout

from utils.concurrency_manager import active_sessions, MAX_CONCURRENT_USERS, clean_stale_sessions

import callbacks.login_callbacks
import callbacks.historical_connectivity_callbacks
import callbacks.user_apk_analysis_callbacks
import callbacks.precomputed_connectivity_callbacks

import os
import time

# Define a simplified navigation bar
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dcc.Link('Home', href='/home', className='nav-link')),
        dbc.NavItem(dcc.Link('Connectivity (Real-time)', href='/historical-connectivity', className='nav-link')),
        dbc.NavItem(dcc.Link('Connectivity (Pre-computed)', href='/precomputed-connectivity', className='nav-link')),
        dbc.NavItem(dcc.Link('Connectivity (Upload APKs)', href='/user-apk-analysis', className='nav-link')),
        dbc.NavItem(html.A('Logout', href='/logout', className='nav-link')),
    ],
    brand="Janus: A Social Science-Oriented App Analysis Suite. A project by Digisilk",
    brand_href="/home",
    color="primary",
    dark=True,
)

# Define the interface navigation bar
app.layout = dbc.Container([
    html.Link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css",
        integrity="sha512-+4zCK9k+qNFUR5X+cKL9EIR+ZOhtIloNl9GIKS57V1MyNsYpYcUrUeQc9vNfzsWfV28IaLL3i96P9sdNyeRssA==",
        crossOrigin="anonymous"
    ),
    dcc.Location(id='url', refresh=True),
    html.Div(id='page-content'),
    # Dummy div for deployment mode toggle
    html.Div(id="dummy-output", style={"display": "none"})
], fluid=True)

# Callbacks that must stay reachable before the user has logged in: the router
# (which decides to show the login page) and the login form itself.
PUBLIC_CALLBACK_OUTPUTS = ('page-content.children', 'login-error')


@server.before_request
def clean_sessions_middleware():
    """Clean stale sessions on each request to prevent resource leaks"""
    clean_stale_sessions()


@server.before_request
def require_login_for_callbacks():
    """Gate the Dash callback endpoint behind authentication.

    display_page() below only chooses which *layout* to render, so on its own it
    stops nothing: Dash callbacks are ordinary POSTs to /_dash-update-component,
    and every analysis callback is registered globally at import time. Without
    this guard an unauthenticated caller can invoke them directly - starting
    AndroZoo downloads, writing uploaded files - by naming the component IDs,
    which are readable from the client bundle.

    Guarding here rather than in each callback means a newly added callback is
    protected by default instead of only when someone remembers.
    """
    if request.path != '/_dash-update-component':
        return None
    if current_user.is_authenticated:
        return None

    body = request.get_json(silent=True) or {}
    output = body.get('output', '')
    if any(public in output for public in PUBLIC_CALLBACK_OUTPUTS):
        return None

    return {'error': 'authentication required'}, 401


@server.route('/logout')
@login_required
def logout():
    """Log out and return to the login page.

    The navbar has always linked here, but the route itself was missing, so
    clicking 'Logout' returned a 404 and left the session active.
    """
    logout_user()
    return redirect('/login')

# Update the page based on the current URL
@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    # Always show login page if user is not authenticated
    if pathname == '/login' or not current_user.is_authenticated:
        return login.layout
    
    # Show navbar only if user is authenticated
    if current_user.is_authenticated:
        if pathname == '/precomputed-connectivity':
            return html.Div([navbar, precomputed_connectivity.layout])
        elif pathname == '/historical-connectivity':
            return html.Div([navbar, historical_connectivity.layout])
        elif pathname == '/user-apk-analysis':
            return html.Div([navbar, user_apk_analysis.layout])
        elif pathname == '/' or pathname == '/home':
            return html.Div([navbar, home_layout.layout])
    
    # Default case - show home page
    return html.Div([navbar, home_layout.layout])

# Register callbacks
callbacks.login_callbacks.register_callbacks(app, User)


def check_prerequisites():
    """Check if required database files exist before starting the web app"""
    required_files = [
        'androzoo.db',
        'filtered_package_ids_with_counts10_ver.json'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ ERROR: Required database files are missing!")
        print("Missing files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\n🔧 Please run the database bootstrap script first:")
        print("   python bootstrap_database.py")
        print("\nThis will download and setup the required database files.")
        return False
    
    print("✅ All required database files found.")
    return True


# Registered at module level, not inside the __main__ block where it used to
# live: under a production WSGI server (gunicorn index:server) that block never
# runs, so this route silently did not exist in exactly the deployment where
# an operator would most want it.
@server.route('/admin/status')
@login_required
def server_status():
    # Clean stale sessions first
    clean_stale_sessions()

    # Return status information
    status = {
        'active_sessions': len(active_sessions),
        'max_concurrent_users': MAX_CONCURRENT_USERS,
        'sessions': [{
            'id': session_id[:8] + '...',  # Show truncated ID for privacy
            'duration_minutes': round((time.time() - data['start_time']) / 60, 1),
            'num_apks': data.get('num_apks', 0)
        } for session_id, data in active_sessions.items()]
    }

    # Format as HTML
    html_content = f"""
    <h1>Server Status</h1>
    <p>Active sessions: {status['active_sessions']} / {status['max_concurrent_users']}</p>
    <h2>Current Sessions:</h2>
    <ul>
    {''.join([f"<li>Session: {s['id']} - Running for {s['duration_minutes']} minutes - Processing {s['num_apks']} APKs</li>" for s in status['sessions']])}
    </ul>
    """
    return html_content


if __name__ == "__main__":
    # Check prerequisites before starting
    if not check_prerequisites():
        exit(1)

    # Get host and port from environment variables with defaults
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'

    print("🚀 Starting Janus...")
    print(f"📡 Server: http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"👥 Max concurrent users: {MAX_CONCURRENT_USERS}")

    app.run(
        debug=debug,
        threaded=True,
        host=host,
        port=port
    )