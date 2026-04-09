"""REST API module for Claw Service Hub.

This module provides RESTful API endpoints for:
- Health check
- Service discovery
- Tunnel management
- Rating management
- User management
"""

from .routes import ApiRoutes

__all__ = ['ApiRoutes']
