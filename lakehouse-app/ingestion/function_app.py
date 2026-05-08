"""Ingestion Function App entry point.

Registers the API and FTP ingestion blueprints into a single Function App.
Azure Functions v2 (Python) loads this file on startup.

To add a new ingestion source:
  1. Add a client in ``api/clients/`` or reuse the FTP helper in ``ftp/function_app.py``.
  2. Add a ``@bp.timer_trigger`` function in the relevant blueprint file.
  3. Add the required Key Vault secrets to ``modules/key_vault/main.tf``.
"""
import azure.functions as func

from api.function_app import bp as api_bp
from ftp.function_app import bp as ftp_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
app.register_functions(api_bp)
app.register_functions(ftp_bp)
