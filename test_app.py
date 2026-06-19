"""Test the FastAPI app directly to see errors."""
from fastapi.testclient import TestClient
import traceback

# Patch to see full errors
from main import app

client = TestClient(app, raise_server_exceptions=False)

response = client.get("/")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS!")
    print(response.text[:300])
else:
    print(f"Error body: {response.text}")

# Also try calling the template directly
print("\n--- Direct template test ---")
from fastapi.templating import Jinja2Templates
import os
base_dir = os.path.dirname(os.path.abspath("main.py"))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))
import inspect
print("TemplateResponse signature:", inspect.signature(templates.TemplateResponse))
