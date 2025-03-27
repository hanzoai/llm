"""
Clean HTML redirects for problematic endpoints.
This module provides clean implementations for the models.html and mcps.html endpoints.
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse


def register_html_redirects(app: FastAPI):
    """
    Register HTML redirect endpoints with the FastAPI app.
    These endpoints redirect to the UI-based views instead of rendering HTML server-side.
    
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