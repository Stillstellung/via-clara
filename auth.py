"""
Authentication and authorization module for Via Clara.
Handles user management, sessions, and permission scoping.
"""

import sqlite3
import os
import json
from functools import wraps
from typing import Optional, Dict, Any, List, Set
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request, redirect, url_for, jsonify


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'via_clara.db')


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0,
            is_guest INTEGER NOT NULL DEFAULT 0,
            nlp_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_type TEXT NOT NULL,
            permission_value TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, permission_type, permission_value)
        );
    """)

    # Ensure admin user exists
    admin = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
            ('admin', generate_password_hash('admin'))
        )

    # Ensure guest user exists
    guest = conn.execute("SELECT id FROM users WHERE is_guest = 1").fetchone()
    if not guest:
        conn.execute(
            "INSERT INTO users (username, is_guest, nlp_enabled) VALUES (?, 1, 0)",
            ('guest',)
        )

    conn.commit()
    conn.close()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the current user from session, or return guest user."""
    user_id = session.get('user_id')
    conn = get_db()

    if user_id:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    else:
        user = conn.execute("SELECT * FROM users WHERE is_guest = 1").fetchone()

    conn.close()
    if user:
        return dict(user)
    return None


def get_user_permissions(user_id: int) -> Dict[str, Set[str]]:
    """Get all permissions for a user, organized by type."""
    conn = get_db()
    rows = conn.execute(
        "SELECT permission_type, permission_value FROM user_permissions WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()

    perms = {'lights': set(), 'groups': set(), 'scenes': set()}
    for row in rows:
        ptype = row['permission_type']
        if ptype in perms:
            perms[ptype].add(row['permission_value'])
    return perms


def user_is_admin(user: Optional[Dict] = None) -> bool:
    """Check if the current/given user is an admin."""
    if user is None:
        user = get_current_user()
    return user is not None and user.get('is_admin', 0) == 1


def filter_lights(lights_data: list, user: Dict) -> list:
    """Filter lights based on user permissions. Admin sees all."""
    if user.get('is_admin'):
        return lights_data

    perms = get_user_permissions(user['id'])
    if not perms['lights'] and not perms['groups']:
        return []  # No permissions = no lights

    filtered = []
    for light in lights_data:
        light_id = str(light.get('id', ''))
        group_id = str(light.get('group', {}).get('id', '')) if light.get('group') else ''

        if light_id in perms['lights'] or group_id in perms['groups']:
            filtered.append(light)

    return filtered


def filter_scenes(scenes_data: list, user: Dict) -> list:
    """Filter scenes based on user permissions. Admin sees all."""
    if user.get('is_admin'):
        return scenes_data

    perms = get_user_permissions(user['id'])
    if not perms['scenes']:
        return []

    return [s for s in scenes_data if s.get('uuid', '') in perms['scenes']]


def can_control_light(user: Dict, selector: str) -> bool:
    """Check if a user can control a light/group given a selector string."""
    if user.get('is_admin'):
        return True

    perms = get_user_permissions(user['id'])

    # Parse selector formats: "id:xxx", "group_id:xxx", "group:name", "all"
    if selector == 'all':
        # 'all' is only allowed if user has at least some permissions
        # But we'll need to rewrite the selector to only target their lights
        return bool(perms['lights'] or perms['groups'])

    if selector.startswith('id:'):
        light_id = selector.split('id:')[1].split('|')[0]  # handle zone selectors
        return light_id in perms['lights']

    if selector.startswith('group_id:'):
        group_id = selector.split('group_id:')[1]
        return group_id in perms['groups']

    if selector.startswith('group:'):
        # Need to resolve group name to ID - allow if any group is permitted
        # This is a best-effort check; the LIFX API will handle the actual filtering
        return bool(perms['groups'])

    return False


def get_user_allowed_selectors(user: Dict) -> str:
    """Get a comma-separated list of selectors the user is allowed to control."""
    if user.get('is_admin'):
        return 'all'

    perms = get_user_permissions(user['id'])
    selectors = []
    for lid in perms['lights']:
        selectors.append(f'id:{lid}')
    for gid in perms['groups']:
        selectors.append(f'group_id:{gid}')
    return ','.join(selectors) if selectors else ''


def require_admin(f):
    """Decorator: require admin access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.get('is_admin'):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def require_login(f):
    """Decorator: require any logged-in user (not guest)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


# Initialize on import
init_db()
