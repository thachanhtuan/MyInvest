"""Check if quotes routes are registered"""
from app.main import app

print("All API routes with /api/quotes:")
for route in app.routes:
    if hasattr(route, 'path') and '/api/quotes' in route.path:
        methods = list(route.methods) if hasattr(route, 'methods') else ['N/A']
        print(f"  {methods[0]:6s} {route.path}")

print("\nAll routes count:", len(app.routes))
