import asyncio

import json

import os

import shutil

import sys

import threading

import time

import uuid

from contextlib import asynccontextmanager

from dataclasses import dataclass, field

from enum import Enum

from pathlib import Path

from typing import Optional


from fastapi import FastAPI, HTTPException, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse, StreamingResponse

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field, field_validator

from slowapi import Limiter, _rate_limit_exceeded_handler

from slowapi.errors import RateLimitExceeded

from slowapi.util import get_remote_address


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from downloader import Downloader  # noqa: E402


TEMP_DIR = Path(os.environ.get("TEMP_DIR", Path(__file__).parent / "temp"))

JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", "3600"))

MAX_DURATION_SECONDS = int(os.environ.get("MAX_DURATION_SECONDS", "7200"))

CLEANUP_INTERVAL_SECONDS = 300


CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://[::1]:5500,https://victorferreiralmeida.github.io",
    ).split(",")
    if origin.strip() and "*" not in origin.strip()
]

IS_PRODUCTION = os.environ.get("ENV", "development").lower() == "production"

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class JobStatus(str, Enum):

    PENDING = "pending"

    RUNNING = "running"

    COMPLETED = "completed"

    FAILED = "failed"


@dataclass
class Job:

    job_id: str

    status: JobStatus = JobStatus.PENDING

    progress: float = 0.0

    message: str = "Aguardando..."

    file_path: Optional[str] = None

    filename: Optional[str] = None

    error: Optional[str] = None

    created_at: float = field(default_factory=time.time)

    events: list = field(default_factory=list)

    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, progress: float, message: str):

        with self.lock:

            self.progress = progress

            self.message = message

            self.events.append(
                {"progress": progress, "message": message, "status": self.status.value}
            )

    def set_status(self, status: JobStatus, message: str = ""):

        with self.lock:

            self.status = status

            if message:

                self.message = message

            event = {
                "progress": self.progress,
                "message": self.message,
                "status": status.value,
            }

            if self.filename:
                event["filename"] = self.filename

            self.events.append(event)


jobs: dict[str, Job] = {}

job_lock = threading.Lock()

active_downloads = 0

download_semaphore = threading.Semaphore(1)


def cleanup_old_jobs():

    now = time.time()

    expired = []

    with job_lock:

        for job_id, job in jobs.items():

            if now - job.created_at > JOB_TTL_SECONDS:

                expired.append(job_id)

        for job_id in expired:

            job = jobs.pop(job_id, None)

            if job and job.file_path and os.path.isfile(job.file_path):

                _remove_path(job.file_path)


def _remove_path(path: str):

    if os.path.isfile(path):

        os.remove(path)

    elif os.path.isdir(path):

        shutil.rmtree(path, ignore_errors=True)

    parent = os.path.dirname(path)

    if parent and os.path.isdir(parent) and not os.listdir(parent):

        shutil.rmtree(parent, ignore_errors=True)


async def periodic_cleanup():

    while True:

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

        cleanup_old_jobs()


@asynccontextmanager
async def lifespan(app: FastAPI):

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    task = asyncio.create_task(periodic_cleanup())

    yield

    task.cancel()

    cleanup_old_jobs()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Media Downloader API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


if IS_PRODUCTION:

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_origin_regex=r"https://.*\.github\.io",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

else:

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class InfoRequest(BaseModel):

    url: str = Field(..., min_length=10)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:

        value = value.strip()

        if not value.startswith(("http://", "https://")):

            raise ValueError("Informe um link válido (http:// ou https://).")

        return value


class DownloadRequest(BaseModel):

    url: str = Field(..., min_length=10)

    format: str = Field(..., pattern="^(mp3|mp4)$")

    format_names: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:

        value = value.strip()

        if not value.startswith(("http://", "https://")):

            raise ValueError("Informe um link válido (http:// ou https://).")

        return value


class InfoResponse(BaseModel):

    title: str

    thumbnail: str

    duration: int

    channel: str

    description: str

    is_playlist: bool

    entry_count: int


class DownloadResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    filename: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/info", response_model=InfoResponse)
@limiter.limit("30/minute")
def get_info(request: Request, body: InfoRequest):

    try:

        info = Downloader(body.url).get_info()

        if info["duration"] > MAX_DURATION_SECONDS:

            raise HTTPException(
                status_code=400,
                detail=f"Vídeo muito longo. Máximo permitido: {MAX_DURATION_SECONDS // 60} minutos.",
            )

        return InfoResponse(**info)

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download", response_model=DownloadResponse)
@limiter.limit("10/minute")
def start_download(request: Request, body: DownloadRequest):

    global active_downloads

    if active_downloads >= 1:

        raise HTTPException(
            status_code=429,
            detail="Já existe um download em andamento. Tente novamente em instantes.",
        )

    try:

        info = Downloader(body.url).get_info()

        if info["duration"] > MAX_DURATION_SECONDS:

            raise HTTPException(
                status_code=400,
                detail=f"Vídeo muito longo. Máximo permitido: {MAX_DURATION_SECONDS // 60} minutos.",
            )

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())

    job_dir = TEMP_DIR / job_id

    job_dir.mkdir(parents=True, exist_ok=True)

    job = Job(job_id=job_id)

    with job_lock:

        jobs[job_id] = job

    thread = threading.Thread(
        target=_run_download,
        args=(job_id, body.url, body.format, body.format_names, str(job_dir)),
        daemon=True,
    )

    thread.start()

    return DownloadResponse(job_id=job_id)


def _filename_from_title(title: str, ext: str) -> str:
    invalid = '<>:"/\\|?*'
    safe = "".join(c for c in title if c not in invalid).strip().rstrip(". ")
    return f"{safe or 'video'}{ext}"


def _run_download(
    job_id: str, url: str, fmt: str, format_names: bool, destination: str
):

    global active_downloads

    job = jobs.get(job_id)

    if not job:

        return

    with download_semaphore:

        active_downloads += 1

        try:

            job.set_status(JobStatus.RUNNING, "Iniciando download...")

            def on_progress(progress: float, message: str):

                job.update(progress, message)

            downloader = Downloader(url, destination, formatar_nomes=format_names)
            # Try to get info early so we can use the original title as fallback
            try:
                downloader_info = downloader.get_info()
            except Exception:
                downloader_info = None

            if fmt == "mp4":

                files = downloader.download_mp4(on_progress=on_progress)

            else:

                files = downloader.download_mp3(on_progress=on_progress)

            if len(files) == 1:
                output_path = files[0]
                filename = os.path.basename(output_path)
                name_root, name_ext = os.path.splitext(filename)

                if not format_names and (
                    not name_root or name_root.lower() == "download"
                ):
                    try:
                        info = downloader_info or downloader.get_info()
                        title = info.get("title")
                        if title:
                            ext = name_ext or os.path.splitext(output_path)[1] or ""
                            desired_name = _filename_from_title(title, ext)
                            if desired_name != filename:
                                new_path = os.path.join(destination, desired_name)
                                os.rename(output_path, new_path)
                                output_path = new_path
                                filename = desired_name
                    except Exception:
                        pass

            else:

                zip_name = f"playlist_{job_id[:8]}.zip"

                output_path = os.path.join(destination, zip_name)

                Downloader.create_zip(files, output_path)

                filename = zip_name

            job.file_path = output_path

            job.filename = filename

            job.update(1.0, "Download concluído!")

            job.set_status(JobStatus.COMPLETED, "Pronto para download")

        except Exception as e:

            job.error = str(e)

            job.set_status(JobStatus.FAILED, str(e))

        finally:

            active_downloads -= 1


@app.get("/api/progress/{job_id}")
async def stream_progress(job_id: str):

    job = jobs.get(job_id)

    if not job:

        raise HTTPException(status_code=404, detail="Job não encontrado")

    async def event_generator():

        sent = 0

        while True:

            with job.lock:

                new_events = job.events[sent:]

                status = job.status

                progress = job.progress

                message = job.message

                error = job.error

                filename = job.filename

            for event in new_events:

                yield f"data: {json.dumps(event)}\n\n"

                sent += 1

            if status in (JobStatus.COMPLETED, JobStatus.FAILED):

                final = {
                    "progress": progress,
                    "message": message,
                    "status": status.value,
                    "filename": filename,
                    "error": error,
                }

                yield f"data: {json.dumps(final)}\n\n"

                break

            yield ": keepalive\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str):

    job = jobs.get(job_id)

    if not job:

        raise HTTPException(status_code=404, detail="Job não encontrado")

    return JobStatusResponse(
        job_id=job_id,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        filename=job.filename,
        error=job.error,
    )


@app.get("/api/file/{job_id}")
def download_file(job_id: str):

    job = jobs.get(job_id)

    if not job:

        raise HTTPException(status_code=404, detail="Job não encontrado")

    if (
        job.status != JobStatus.COMPLETED
        or not job.file_path
        or not os.path.isfile(job.file_path)
    ):

        raise HTTPException(status_code=404, detail="Arquivo não disponível")

    from mimetypes import guess_type

    media_type, _ = guess_type(job.file_path)

    return FileResponse(
        job.file_path,
        filename=job.filename,
        media_type=media_type or "application/octet-stream",
    )


@app.delete("/api/job/{job_id}")
def delete_job(job_id: str):

    with job_lock:

        job = jobs.pop(job_id, None)

    if not job:

        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.file_path:

        _remove_path(job.file_path)

    return {"deleted": True}


if FRONTEND_DIR.is_dir():

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
