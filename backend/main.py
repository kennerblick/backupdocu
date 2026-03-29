from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
import models
from database import engine, get_db, Base

import os, json
from pathlib import Path

# Storage mode: default JSON per User-Wunsch
STORAGE_MODE = os.getenv('STORAGE_MODE', 'json').lower() if os.getenv('STORAGE_MODE') else 'json'
STORAGE_FILE = Path(__file__).parent / 'storage.json'

# DB initialisation happens only im db mode
if STORAGE_MODE == 'db':
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="BackupDocu API", version="1.0.0")


def get_storage_mode() -> str:
    return STORAGE_MODE


def set_storage_mode(mode: str) -> None:
    global STORAGE_MODE
    mode = mode.lower()
    if mode not in ['json', 'db']:
        raise ValueError('Ungültiger Speicher-Modus')
    STORAGE_MODE = mode
    if mode == 'db':
        Base.metadata.create_all(bind=engine)


def _init_storage_file():
    if not STORAGE_FILE.exists():
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            'servers': [], 'sources': [], 'methods': [], 'targets': [], 'jobs': [],
            'next_ids': {'servers': 1, 'sources': 1, 'methods': 1, 'targets': 1, 'jobs': 1}
        }
        STORAGE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')


def _load_storage():
    _init_storage_file()
    return json.loads(STORAGE_FILE.read_text(encoding='utf-8'))


def _save_storage(state):
    STORAGE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')


def _get_json_item(collection, item_id):
    state = _load_storage()
    for v in state[collection]:
        if v.get('id') == item_id:
            return v
    return None


def _delete_json_item(collection, item_id):
    state = _load_storage()
    arr = state[collection]
    new_arr = [v for v in arr if v.get('id') != item_id]
    if len(new_arr) == len(arr):
        return False
    state[collection] = new_arr
    _save_storage(state)
    return True


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class ServerBase(BaseModel):
    name: str
    hostname: Optional[str] = None
    type: Optional[str] = "physical"
    os: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None

class ServerCreate(ServerBase): pass
class ServerOut(ServerBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True


class BackupTargetBase(BaseModel):
    name: str
    type: str
    hostname: Optional[str] = None
    path: Optional[str] = None
    capacity_tb: Optional[float] = None
    description: Optional[str] = None

class BackupTargetCreate(BackupTargetBase): pass
class BackupTargetOut(BackupTargetBase):
    id: int
    class Config: from_attributes = True


class BackupSourceBase(BaseModel):
    server_id: int
    name: str
    type: str
    path: Optional[str] = None
    size_gb: Optional[float] = None
    description: Optional[str] = None

class BackupSourceCreate(BackupSourceBase): pass
class BackupSourceOut(BackupSourceBase):
    id: int
    class Config: from_attributes = True


class BackupMethodBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class BackupMethodCreate(BackupMethodBase): pass
class BackupMethodOut(BackupMethodBase):
    id: int
    class Config: from_attributes = True


class BackupJobBase(BaseModel):
    name: str
    source_id: int
    method_id: Optional[int] = None
    primary_target_id: Optional[int] = None
    tape_target_id: Optional[int] = None
    offsite_target_id: Optional[int] = None
    schedule: Optional[str] = None
    retention: Optional[str] = None
    gfs_policy: Optional[str] = None
    is_encrypted: bool = False
    is_compressed: bool = True
    status: str = "active"
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    notes: Optional[str] = None

class BackupJobCreate(BackupJobBase): pass
class BackupJobOut(BackupJobBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True


# ─── API Routes ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# Servers
@app.get("/api/servers", response_model=list[ServerOut])
def list_servers(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        return _load_storage()['servers']
    return db.query(models.Server).order_by(models.Server.name).all()

@app.post("/api/servers", response_model=ServerOut, status_code=201)
def create_server(data: ServerCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage()
        nid = state['next_ids']['servers']
        item = data.model_dump()
        item['id'] = nid
        item['created_at'] = datetime.utcnow().isoformat()
        state['next_ids']['servers'] += 1
        state['servers'].append(item)
        _save_storage(state)
        return item
    obj = models.Server(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.put("/api/servers/{sid}", response_model=ServerOut)
def update_server(sid: int, data: ServerCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage()
        obj = _get_json_item('servers', sid)
        if not obj: raise HTTPException(404, "Server not found")
        for k, v in data.model_dump().items(): obj[k] = v
        obj['updated_at'] = datetime.utcnow().isoformat()
        _save_storage(state)
        return obj
    obj = db.query(models.Server).get(sid)
    if not obj: raise HTTPException(404, "Server not found")
    for k, v in data.model_dump().items(): setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit(); db.refresh(obj)
    return obj

@app.delete("/api/servers/{sid}", status_code=204)
def delete_server(sid: int, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        if not _delete_json_item('servers', sid): raise HTTPException(404, "Server not found")
        return
    obj = db.query(models.Server).get(sid)
    if not obj: raise HTTPException(404, "Server not found")
    db.delete(obj); db.commit()


# Backup Targets
@app.get("/api/targets", response_model=list[BackupTargetOut])
def list_targets(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        return _load_storage()['targets']
    return db.query(models.BackupTarget).order_by(models.BackupTarget.name).all()

@app.post("/api/targets", response_model=BackupTargetOut, status_code=201)
def create_target(data: BackupTargetCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); nid = state['next_ids']['targets'];
        item = data.model_dump(); item['id']=nid; item['created_at']=datetime.utcnow().isoformat();
        state['next_ids']['targets'] += 1; state['targets'].append(item); _save_storage(state); return item
    obj = models.BackupTarget(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.put("/api/targets/{tid}", response_model=BackupTargetOut)
def update_target(tid: int, data: BackupTargetCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); obj = _get_json_item('targets', tid)
        if not obj: raise HTTPException(404)
        for k,v in data.model_dump().items(): obj[k]=v
        obj['updated_at'] = datetime.utcnow().isoformat(); _save_storage(state); return obj
    obj = db.query(models.BackupTarget).get(tid)
    if not obj: raise HTTPException(404)
    for k, v in data.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/targets/{tid}", status_code=204)
def delete_target(tid: int, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        if not _delete_json_item('targets', tid): raise HTTPException(404)
        return
    obj = db.query(models.BackupTarget).get(tid)
    if not obj: raise HTTPException(404)
    db.delete(obj); db.commit()


# Backup Sources
@app.get("/api/sources", response_model=list[BackupSourceOut])
def list_sources(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        return _load_storage()['sources']
    return db.query(models.BackupSource).order_by(models.BackupSource.name).all()

@app.post("/api/sources", response_model=BackupSourceOut, status_code=201)
def create_source(data: BackupSourceCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); nid = state['next_ids']['sources'];
        item = data.model_dump(); item['id']=nid; item['created_at'] = datetime.utcnow().isoformat();
        state['next_ids']['sources'] += 1; state['sources'].append(item); _save_storage(state); return item
    obj = models.BackupSource(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.put("/api/sources/{sid}", response_model=BackupSourceOut)
def update_source(sid: int, data: BackupSourceCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); obj = _get_json_item('sources', sid)
        if not obj: raise HTTPException(404)
        for k,v in data.model_dump().items(): obj[k]=v
        obj['updated_at'] = datetime.utcnow().isoformat(); _save_storage(state); return obj
    obj = db.query(models.BackupSource).get(sid)
    if not obj: raise HTTPException(404)
    for k, v in data.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/sources/{sid}", status_code=204)
def delete_source(sid: int, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        if not _delete_json_item('sources', sid): raise HTTPException(404)
        return
    obj = db.query(models.BackupSource).get(sid)
    if not obj: raise HTTPException(404)
    db.delete(obj); db.commit()


# Backup Methods
@app.get("/api/methods", response_model=list[BackupMethodOut])
def list_methods(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        return _load_storage()['methods']
    return db.query(models.BackupMethod).order_by(models.BackupMethod.name).all()

@app.post("/api/methods", response_model=BackupMethodOut, status_code=201)
def create_method(data: BackupMethodCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); nid = state['next_ids']['methods'];
        item = data.model_dump(); item['id']=nid; item['created_at'] = datetime.utcnow().isoformat();
        state['next_ids']['methods'] += 1; state['methods'].append(item); _save_storage(state); return item
    obj = models.BackupMethod(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.put("/api/methods/{mid}", response_model=BackupMethodOut)
def update_method(mid: int, data: BackupMethodCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); obj = _get_json_item('methods', mid)
        if not obj: raise HTTPException(404)
        for k,v in data.model_dump().items(): obj[k]=v
        obj['updated_at'] = datetime.utcnow().isoformat(); _save_storage(state); return obj
    obj = db.query(models.BackupMethod).get(mid)
    if not obj: raise HTTPException(404)
    for k, v in data.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/methods/{mid}", status_code=204)
def delete_method(mid: int, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        if not _delete_json_item('methods', mid): raise HTTPException(404)
        return
    obj = db.query(models.BackupMethod).get(mid)
    if not obj: raise HTTPException(404)
    db.delete(obj); db.commit()


# Backup Jobs
@app.get("/api/jobs", response_model=list[BackupJobOut])
def list_jobs(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        return _load_storage()['jobs']
    return db.query(models.BackupJob).order_by(models.BackupJob.name).all()

@app.post("/api/jobs", response_model=BackupJobOut, status_code=201)
def create_job(data: BackupJobCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); nid = state['next_ids']['jobs'];
        item = data.model_dump(); item['id']=nid; item['created_at'] = datetime.utcnow().isoformat();
        state['next_ids']['jobs'] += 1; state['jobs'].append(item); _save_storage(state); return item
    obj = models.BackupJob(**data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.put("/api/jobs/{jid}", response_model=BackupJobOut)
def update_job(jid: int, data: BackupJobCreate, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage(); obj = _get_json_item('jobs', jid)
        if not obj: raise HTTPException(404)
        for k,v in data.model_dump().items(): obj[k]=v
        obj['updated_at'] = datetime.utcnow().isoformat(); _save_storage(state); return obj
    obj = db.query(models.BackupJob).get(jid)
    if not obj: raise HTTPException(404)
    for k, v in data.model_dump().items(): setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/jobs/{jid}", status_code=204)
def delete_job(jid: int, db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        if not _delete_json_item('jobs', jid): raise HTTPException(404)
        return
    obj = db.query(models.BackupJob).get(jid)
    if not obj: raise HTTPException(404)
    db.delete(obj); db.commit()


# ─── Storage config ─────────────────────────────────────────────────────────

@app.get("/api/config/storage")
def get_storage_config():
    return {"mode": get_storage_mode()}

@app.post("/api/config/storage")
def set_storage_config(mode: Literal['json', 'db']):
    try:
        set_storage_mode(mode)
        return {"mode": get_storage_mode()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Topology Endpoint (für Flow-Diagramm) ───────────────────────────────────

@app.get("/api/topology")
def get_topology(db: Session = Depends(get_db)):
    """Gibt alle Daten für das Flow-Diagramm zurück"""
    if get_storage_mode() == 'json':
        state = _load_storage()
        servers = state['servers']; sources = state['sources']; methods = state['methods']; targets = state['targets']; jobs = state['jobs']
    else:
        servers = db.query(models.Server).all()
        sources = db.query(models.BackupSource).all()
        methods = db.query(models.BackupMethod).all()
        targets = db.query(models.BackupTarget).all()
        jobs = db.query(models.BackupJob).all()

    return {
        "servers": [{"id": s.id, "name": s.name, "hostname": s.hostname,
                     "type": s.type, "os": s.os, "role": s.role} for s in servers],
        "sources": [{"id": s.id, "server_id": s.server_id, "name": s.name,
                     "type": s.type, "path": s.path, "description": s.description} for s in sources],
        "methods": [{"id": m.id, "name": m.name, "type": m.type} for m in methods],
        "targets": [{"id": t.id, "name": t.name, "type": t.type,
                     "hostname": t.hostname, "capacity_tb": float(t.capacity_tb) if t.capacity_tb else None} for t in targets],
        "jobs": [{"id": j.id, "name": j.name, "source_id": j.source_id,
                  "method_id": j.method_id, "primary_target_id": j.primary_target_id,
                  "tape_target_id": j.tape_target_id, "offsite_target_id": j.offsite_target_id,
                  "schedule": j.schedule, "retention": j.retention,
                  "status": j.status, "last_result": j.last_result,
                  "is_encrypted": j.is_encrypted, "gfs_policy": j.gfs_policy} for j in jobs],
    }


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    if get_storage_mode() == 'json':
        state = _load_storage();
        jobs = state['jobs']
        return {
            "servers": len(state['servers']),
            "sources": len(state['sources']),
            "jobs": len(jobs),
            "jobs_active": len([j for j in jobs if j.get('status') == 'active']),
            "jobs_with_tape": len([j for j in jobs if j.get('tape_target_id')]),
            "jobs_with_offsite": len([j for j in jobs if j.get('offsite_target_id')]),
            "targets": len(state['targets']),
        }
    return {
        "servers": db.query(models.Server).count(),
        "sources": db.query(models.BackupSource).count(),
        "jobs": db.query(models.BackupJob).count(),
        "jobs_active": db.query(models.BackupJob).filter(models.BackupJob.status == "active").count(),
        "jobs_with_tape": db.query(models.BackupJob).filter(models.BackupJob.tape_target_id.isnot(None)).count(),
        "jobs_with_offsite": db.query(models.BackupJob).filter(models.BackupJob.offsite_target_id.isnot(None)).count(),
        "targets": db.query(models.BackupTarget).count(),
    }
