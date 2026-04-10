"""
extensions.py — Shared Extension Instances

We create these here (without an app) so they can be imported
everywhere without triggering circular imports.
The actual initialization happens in create_app() via .init_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt      import Bcrypt
from flask_jwt_extended import JWTManager

db     = SQLAlchemy()   # ORM for database operations
bcrypt = Bcrypt()       # Password hashing
jwt    = JWTManager()   # JWT token management
