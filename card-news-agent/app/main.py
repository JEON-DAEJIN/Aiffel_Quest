import io
import json
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import db, engine
from .schemas import CreateRunRequest, RegenerateCardRequest, ReviewRequest, SelectRequest
from .topics.registry import get_topic, list_topics

load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
RUNS_MEDIA_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"
RUNS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="card-news-agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# data/runs만 노출한다 — DB 파일이 있는 data/ 루트 전체는 절대 정적 서빙하지 않는다.
app.mount("/media", StaticFiles(directory=RUNS_MEDIA_DIR), name="media")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/topics")
async def api_list_topics():
    return [
        {
            "topic_id": t.topic_id,
            "display_name": t.display_name,
            "selection_range": t.selection_range,
            "candidate_count_range": t.candidate_count_range,
            "storyboard_card_range": t.storyboard_card_range,
            "input_mode": t.input_mode,
            "cta_card": t.cta_card,
        }
        for t in list_topics()
    ]


@app.post("/runs")
async def create_run(req: CreateRunRequest, bg: BackgroundTasks):
    try:
        topic = get_topic(req.topic_id)
    except KeyError:
        raise HTTPException(404, f"unknown topic_id: {req.topic_id}")
    if topic.input_mode == "source_text" and not (req.source_text or "").strip():
        raise HTTPException(400, "this topic requires source_text")
    if topic.cta_card and not (req.source_url or "").strip():
        raise HTTPException(400, "this topic requires source_url")
    run_id = db.insert_run(
        topic_id=topic.topic_id,
        status="running",
        stage="research",
        source_text=req.source_text,
        source_url=req.source_url,
    )
    bg.add_task(engine.run_research_stage, run_id, topic)
    return {"run_id": run_id}


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    row = db.get_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    return row


@app.post("/runs/{run_id}/select")
async def select_candidates(run_id: str, req: SelectRequest, bg: BackgroundTasks):
    try:
        row = db.require_stage(run_id, status="waiting_for_user", stage="await_selection")
    except LookupError:
        raise HTTPException(404, "run not found")
    except ValueError as e:
        raise HTTPException(409, str(e))

    topic = get_topic(row["topic_id"])
    lo, hi = topic.selection_range
    if not (lo <= len(req.candidate_ids) <= hi):
        raise HTTPException(400, f"select between {lo} and {hi} candidates")

    db.update_run(
        run_id,
        status="running",
        stage="verify_storyboard",
        selected_candidates_json=json.dumps(req.candidate_ids),
    )
    bg.add_task(engine.run_verification_stage, run_id, topic)
    return {"ok": True}


@app.post("/runs/{run_id}/review")
async def review_storyboard(run_id: str, req: ReviewRequest, bg: BackgroundTasks):
    try:
        row = db.require_stage(run_id, status="waiting_for_user", stage="await_approval")
    except LookupError:
        raise HTTPException(404, "run not found")
    except ValueError as e:
        raise HTTPException(409, str(e))

    if req.action == "approve":
        topic = get_topic(row["topic_id"])
        db.update_run(run_id, status="running", stage="generate_images")
        bg.add_task(engine.run_image_generation_stage, run_id, topic)
        return {"ok": True}
    if req.action != "revise":
        raise HTTPException(400, "action must be 'approve' or 'revise'")

    topic = get_topic(row["topic_id"])
    db.update_run(run_id, status="running", stage="verify_storyboard")
    bg.add_task(engine.run_revision_stage, run_id, topic, req.notes)
    return {"ok": True}


@app.post("/runs/{run_id}/retry")
async def retry_run(run_id: str, bg: BackgroundTasks):
    row = db.get_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    if row["status"] != "failed":
        raise HTTPException(400, "only failed runs can be retried")

    topic = get_topic(row["topic_id"])
    db.update_run(run_id, status="running", error_message=None, retry_count=row["retry_count"] + 1)
    stage_fn = {
        "research": engine.run_research_stage,
        "verify_storyboard": engine.run_verification_stage,
        "generate_images": engine.run_image_generation_stage,
    }.get(row["stage"], engine.run_verification_stage)
    bg.add_task(stage_fn, run_id, topic)
    return {"ok": True}


@app.post("/runs/{run_id}/regenerate_card")
async def regenerate_card(run_id: str, req: RegenerateCardRequest, bg: BackgroundTasks):
    try:
        row = db.require_stage(run_id, status="waiting_for_user", stage="await_review")
    except LookupError:
        raise HTTPException(404, "run not found")
    except ValueError as e:
        raise HTTPException(409, str(e))

    topic = get_topic(row["topic_id"])
    db.update_run(run_id, status="running")
    bg.add_task(engine.run_single_card_image, run_id, topic, req.card_number)
    return {"ok": True}


@app.post("/runs/{run_id}/finish")
async def finish_run(run_id: str):
    try:
        db.require_stage(run_id, status="waiting_for_user", stage="await_review")
    except LookupError:
        raise HTTPException(404, "run not found")
    except ValueError as e:
        raise HTTPException(409, str(e))

    db.update_run(run_id, status="completed", stage="done")
    return {"ok": True}


@app.get("/runs/{run_id}/download")
async def download_run(run_id: str):
    row = db.get_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    if row["status"] != "completed":
        raise HTTPException(400, "run is not completed yet")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for record in row.get("images") or []:
            final_path = record.get("final_path")
            if final_path and Path(final_path).exists():
                zf.write(final_path, arcname=Path(final_path).name)
    # StreamingResponse(buf, ...)는 BytesIO를 줄바꿈(\n) 기준으로 쪼개 보내는데, 바이너리
    # zip 데이터엔 그 바이트가 우연히 수만 번 등장해 수만 개의 아주 작은 전송으로 쪼개져
    # 실제로 다운로드가 100초 넘게 걸리는 것을 확인했다. 이미 메모리에 전부 압축해둔
    # 상태이므로 통짜 bytes로 한 번에 응답한다.
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="card-news-{run_id}.zip"'},
    )
