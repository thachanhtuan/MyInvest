"""Check analytics routes"""
from app.routers.analytics import router

print("Routes in analytics router:")
for r in router.routes:
    methods = list(r.methods) if hasattr(r, 'methods') else ['N/A']
    print(f"  {methods[0]:6s} {r.path}")
