from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import costs, dashboard, decisions, fleet, invoices, operators, pickups, site_checks, value_summary, containers

app = FastAPI(title="Customer portal API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(invoices.router)
app.include_router(costs.router)
app.include_router(containers.router)
app.include_router(value_summary.value_router)
app.include_router(operators.router)
app.include_router(decisions.router)
for extra in (dashboard, pickups, site_checks, fleet, value_summary):
    app.include_router(extra.router)
