"""Test direct import of quotes router"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.routers.quotes import router
    print(f"✓ Router imported successfully")
    print(f"✓ Router prefix: {router.prefix}")
    print(f"✓ Routes count: {len(router.routes)}")
    print(f"\nRegistered routes:")
    for route in router.routes:
        methods = list(route.methods) if hasattr(route, 'methods') else ['N/A']
        print(f"  {methods[0]:6s} {route.path}")
except Exception as e:
    print(f"✗ Error importing router: {e}")
    import traceback
    traceback.print_exc()
