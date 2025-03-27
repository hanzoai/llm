#!/usr/bin/env python3
"""
Module for clean HTML redirects using FastAPI.
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse


def register_redirects(app: FastAPI):
    """
    Register clean HTML redirect endpoints with the FastAPI app.
    
    Args:
        app: The FastAPI application instance
    """
    
    @app.get("/models.html", response_class=RedirectResponse)
    async def redirect_models_html():
        """Redirect to UI-based models view"""
        return RedirectResponse("/ui/models", status_code=307)
    
    @app.get("/mcps.html", response_class=RedirectResponse)
    async def redirect_mcps_html():
        """Redirect to UI-based MCP servers view"""
        return RedirectResponse("/ui/mcp-servers", status_code=307)
    
    return app