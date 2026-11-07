from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import costs, decisions, invoices, operators, weight_ideas

app = FastAPI(title="Customer portal API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(invoices.router)
app.include_router(costs.router)
app.include_router(operators.router)
app.include_router(decisions.router)
app.include_router(weight_ideas.router)
