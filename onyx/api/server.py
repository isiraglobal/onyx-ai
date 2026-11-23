"""FastAPI REST and WebSocket gateway for ONYX."""

import asyncio
from pathlib import Path
import time
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from contextlib import asynccontextmanager

from onyx.config import OnyxConfig, load_config
from onyx.core.orchestrator import OnyxCore
from onyx.models.detector import detect_hardware
from onyx.models.benchmark import benchmark_model
from onyx.memory.categories import MemoryCategory
from onyx.learning.dataset import DatasetBuilder, TrainingExample
from onyx.learning.finetune import TrainingConfig, CheckpointManager, FinetuneWorkflow
from onyx.learning.ingestion import IngestionPipeline
from onyx.sync.bundle import SyncBundleManager
from onyx.security.audit import verify_auth_token
from onyx.qla.deal_flow import DealFlowEngine
from onyx.qla.financial import FinancialAnalysisEngine
from onyx.qla.dream_team import DreamTeamEngine
from onyx.qla.financing import FinancingEngine
from onyx.qla.execution import ExecutionEngine
from onyx.qla.models import DealStage, DreamTeamRole, CandidateStatus


def create_app(core: Optional[OnyxCore] = None, config: Optional[OnyxConfig] = None) -> FastAPI:
    cfg = config or load_config()
    app_core = core or OnyxCore(config=cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await app_core.initialize()
        yield

    app = FastAPI(
        title="ONYX Intelligence Platform",
        version="0.2.0",
        description="Portable, Self-Improving Personal AI Gateway",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # State
    app.state.core = app_core
    app.state.config = cfg

    # Authentication dependency
    async def check_auth(authorization: Optional[str] = Header(None)):
        if cfg.server.require_auth:
            token = authorization.replace("Bearer ", "") if authorization else None
            if not verify_auth_token(token, cfg.server.auth_token):
                raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing authentication token.")


    # --- Pydantic Request Models ---
    class ChatRequest(BaseModel):
        message: str
        model: Optional[str] = None

    class MemoryAddRequest(BaseModel):
        content: str
        category: str = "knowledge"
        metadata: Optional[Dict[str, Any]] = None

    class IngestRequest(BaseModel):
        file_path: str
        category: str = "knowledge"

    class TaskRequest(BaseModel):
        goal: str
        agent: Optional[str] = None

    class SpawnAgentRequest(BaseModel):
        name: str
        role: str
        instructions: str
        tools: List[str] = []

    class AddDealRequest(BaseModel):
        company_name: str
        industry: str
        revenue: float
        ebitda: float
        asking_price: float
        location: str = ""
        website: str = ""
        seller_motivation: str = ""
        next_action: str = "Request 3 years P&L and tax returns"

    class UpdateDealStageRequest(BaseModel):
        stage: str
        next_action: Optional[str] = None

    class FinancialAnalysisRequest(BaseModel):
        mode: str = "ratios"  # ratios | lbo_model | bogus_books_audit
        revenue: float = 0.0
        ebitda: float = 0.0
        purchase_price: float = 0.0
        cogs: Optional[float] = None
        annual_debt_service: float = 0.0
        seller_note_pct: float = 0.25
        has_tax_returns: bool = False
        tax_return_revenue: Optional[float] = None
        largest_customer_pct: float = 10.0
        top_3_customers_pct: float = 25.0
        owner_actively_runs_daily_ops: bool = True
        years_of_financial_records: int = 3

    class AddCandidateRequest(BaseModel):
        name: str
        role: str
        background: str = ""
        credentials: str = ""
        compensation_terms: str = "1-2% equity at close"

    # --- REST Endpoints ---

    @app.get("/api/v1/system/health")
    async def get_system_health():
        hw = detect_hardware()
        records_count = len(await app_core.memory.store.export_all())
        active_model = app_core.model_registry.active_adapter_name or "mock"
        return {
            "status": "healthy",
            "system_name": cfg.identity.role,
            "version": "0.2.0",
            "active_model": active_model,
            "memory_records_count": records_count,
            "hardware": hw.to_dict(),
            "uptime_seconds": time.time(),
        }

    @app.post("/api/v1/chat", dependencies=[Depends(check_auth)])
    async def post_chat(req: ChatRequest):
        reply = await app_core.process_message(req.message)
        return {"response": reply, "model": app_core.model_registry.active_adapter_name}

    @app.get("/api/v1/models")
    async def list_models():
        return {
            "active": app_core.model_registry.active_adapter_name,
            "models": app_core.model_registry.list_models(),
            "hardware": detect_hardware().to_dict(),
        }

    @app.post("/api/v1/models/benchmark")
    async def run_model_benchmark():
        adapter = await app_core.model_registry.get_or_fallback()
        res = await benchmark_model(adapter)
        return res.to_dict()

    @app.get("/api/v1/memory")
    async def get_memories(query: Optional[str] = None, category: Optional[str] = None, limit: int = 50):
        if query:
            cat_enum = MemoryCategory(category) if category else None
            results = await app_core.memory.recall(query=query, category=cat_enum, limit=limit)
            return [{"record": r.to_dict(), "similarity": round(s, 4)} for r, s in results]
        else:
            cat_enum = MemoryCategory(category) if category else None
            records = await app_core.memory.store.filter_metadata(category=cat_enum, limit=limit)
            return [r.to_dict() for r in records]

    @app.post("/api/v1/memory", dependencies=[Depends(check_auth)])
    async def add_memory(req: MemoryAddRequest):
        cat_enum = MemoryCategory(req.category)
        rec = await app_core.memory.remember(content=req.content, category=cat_enum, metadata=req.metadata)
        return {"status": "saved", "record": rec.to_dict()}

    @app.delete("/api/v1/memory/{record_id}", dependencies=[Depends(check_auth)])
    async def delete_memory(record_id: str):
        success = await app_core.memory.store.delete(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory record not found")
        return {"status": "deleted", "id": record_id}

    @app.post("/api/v1/learning/ingest", dependencies=[Depends(check_auth)])
    async def ingest_document(req: IngestRequest):
        pipeline = IngestionPipeline(memory=app_core.memory)
        cat_enum = MemoryCategory(req.category)
        res = await pipeline.ingest_file(req.file_path, category=cat_enum)
        return res

    @app.get("/api/v1/agents")
    async def list_agents():
        if not app_core.agent_pool:
            return []
        return app_core.agent_pool.list_agents()

    @app.post("/api/v1/agents/task", dependencies=[Depends(check_auth)])
    async def run_agent_task(req: TaskRequest):
        if not app_core.agent_pool:
            raise HTTPException(status_code=500, detail="Agent pool not initialized")
        target = app_core.agent_pool.get_agent(req.agent or "supervisor")
        if not target:
            raise HTTPException(status_code=404, detail=f"Agent '{req.agent}' not found")

        from onyx.agents.base import AgentTask
        task = AgentTask(goal=req.goal, assigned_agent=target.name)
        res = await target.execute_task(task)
        return {
            "status": res.status.value,
            "result": res.result,
            "error": res.error,
            "messages": [{"role": m.role, "content": m.content} for m in res.messages],
        }

    @app.post("/api/v1/agents/spawn", dependencies=[Depends(check_auth)])
    async def spawn_agent(req: SpawnAgentRequest):
        if not app_core.agent_pool:
            raise HTTPException(status_code=500, detail="Agent pool not initialized")
        agent = app_core.agent_pool.spawn_temporary_agent(
            name=req.name,
            role_description=req.role,
            instructions=req.instructions,
            allowed_tools=req.tools,
        )
        return {"status": "spawned", "agent": {"name": agent.name, "role": agent.role_description}}

    # --- QLA Deal-Making Operating System Endpoints ---
    qla_deal_flow = DealFlowEngine()
    qla_dream_team = DreamTeamEngine()
    qla_execution = ExecutionEngine(deal_engine=qla_deal_flow)
    qla_financing = FinancingEngine()

    @app.get("/api/v1/qla/pipeline")
    async def get_qla_pipeline():
        summary = qla_deal_flow.get_pipeline_summary()
        deals = [d.to_dict() for d in qla_deal_flow.list_deals()]
        return {"summary": summary, "deals": deals}

    @app.post("/api/v1/qla/deals", dependencies=[Depends(check_auth)])
    async def add_qla_deal(req: AddDealRequest):
        deal = qla_deal_flow.add_opportunity(
            company_name=req.company_name,
            industry=req.industry,
            revenue=req.revenue,
            ebitda=req.ebitda,
            asking_price=req.asking_price,
            location=req.location,
            website=req.website,
            seller_motivation=req.seller_motivation,
            next_action=req.next_action,
        )
        return {"status": "created", "deal": deal.to_dict()}

    @app.patch("/api/v1/qla/deals/{deal_id}/stage", dependencies=[Depends(check_auth)])
    async def update_qla_deal_stage(deal_id: str, req: UpdateDealStageRequest):
        try:
            stage = DealStage(req.stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {req.stage}")
        updated = qla_deal_flow.update_stage(deal_id, stage, next_action=req.next_action)
        if not updated:
            raise HTTPException(status_code=404, detail="Deal not found")
        return {"status": "updated", "deal": updated.to_dict()}

    @app.get("/api/v1/qla/deals/weakest")
    async def get_weakest_deal():
        weakest = qla_deal_flow.find_weakest_deal()
        return {"weakest_deal": weakest}

    @app.post("/api/v1/qla/analyze", dependencies=[Depends(check_auth)])
    async def run_qla_financial_analysis(req: FinancialAnalysisRequest):
        if req.mode == "ratios":
            res = FinancialAnalysisEngine.calculate_ratios(
                revenue=req.revenue,
                ebitda=req.ebitda,
                cogs=req.cogs,
                annual_debt_service=req.annual_debt_service,
            )
        elif req.mode == "lbo_model":
            res = FinancialAnalysisEngine.model_lbo_structure(
                purchase_price=req.purchase_price,
                ebitda=req.ebitda,
                seller_note_pct=req.seller_note_pct,
            )
        elif req.mode == "bogus_books_audit":
            res = FinancialAnalysisEngine.audit_bogus_financial_books(
                has_tax_returns=req.has_tax_returns,
                tax_return_revenue=req.tax_return_revenue,
                reported_pl_revenue=req.revenue,
                largest_customer_pct=req.largest_customer_pct,
                top_3_customers_pct=req.top_3_customers_pct,
                owner_actively_runs_daily_ops=req.owner_actively_runs_daily_ops,
                years_of_financial_records=req.years_of_financial_records,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown mode: {req.mode}")
        return {"mode": req.mode, "results": res}

    @app.get("/api/v1/qla/dream-team")
    async def get_qla_dream_team():
        readiness = qla_dream_team.assess_dream_team_readiness()
        candidates = [c.to_dict() for c in qla_dream_team.list_candidates()]
        return {"readiness": readiness, "candidates": candidates}

    @app.post("/api/v1/qla/dream-team", dependencies=[Depends(check_auth)])
    async def add_qla_candidate(req: AddCandidateRequest):
        try:
            role = DreamTeamRole(req.role)
        except ValueError:
            role = DreamTeamRole.BOARD_DIRECTOR
        cand = qla_dream_team.add_candidate(
            name=req.name,
            role=role,
            background=req.background,
            credentials=req.credentials,
            compensation_terms=req.compensation_terms,
        )
        return {"status": "added", "candidate": cand.to_dict()}

    @app.get("/api/v1/qla/briefing")
    async def get_daily_briefing():
        return qla_execution.get_morning_briefing()

    # --- WebSocket Streaming Endpoint ---

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                # Stream response word by word
                async for chunk in app_core.stream_message(data):
                    await websocket.send_json({
                        "delta": chunk.delta,
                        "is_finished": chunk.is_finished,
                    })
        except WebSocketDisconnect:
            pass

    # --- Mount Web Interface ---
    ui_dir = Path(__file__).resolve().parent.parent / "interface"
    if ui_dir.exists():
        app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def serve_index():
            index_path = ui_dir / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
            return HTMLResponse(content="<h1>ONYX Interface Initializing...</h1>")

    return app
