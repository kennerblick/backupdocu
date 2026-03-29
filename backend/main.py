from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import json

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

COLLECTION_FILES = {
    'servers': DATA_DIR / 'servers.json',
    'sources': DATA_DIR / 'sources.json',
    'methods': DATA_DIR / 'methods.json',
    'targets': DATA_DIR / 'targets.json',
    'jobs': DATA_DIR / 'jobs.json',
}

for p in COLLECTION_FILES.values():
    if not p.exists():
        p.write_text('[]', encoding='utf-8')


def load_collection(name: str):
    path = COLLECTION_FILES.get(name)
    if not path:
        raise ValueError('Unknown collection')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        data = []
    return data


def save_collection(name: str, data):
    path = COLLECTION_FILES.get(name)
    if not path:
        raise ValueError('Unknown collection')
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def next_id(items):
    return max((item.get('id', 0) for item in items), default=0) + 1


def get_item(collection: str, item_id: int):
    items = load_collection(collection)
    for item in items:
        if item.get('id') == item_id:
            return item
    return None


def upsert_item(collection: str, item_id: Optional[int], payload: dict):
    items = load_collection(collection)
    if item_id is None:
        payload['id'] = next_id(items)
        payload['created_at'] = datetime.utcnow().isoformat()
        payload['updated_at'] = datetime.utcnow().isoformat()
        items.append(payload)
        save_collection(collection, items)
        return payload

    existing = get_item(collection, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail='Not found')
    for key, value in payload.items():
        existing[key] = value
    existing['updated_at'] = datetime.utcnow().isoformat()
    save_collection(collection, items)
    return existing


def delete_item(collection: str, item_id: int):
    items = load_collection(collection)
    new_items = [item for item in items if item.get('id') != item_id]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail='Not found')
    save_collection(collection, new_items)


# Schemas
class ServerBase(BaseModel):
    name: str
    hostname: Optional[str] = None
    type: Optional[str] = 'physical'
    os: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None


class BackupTargetBase(BaseModel):
    name: str
    type: str
    hostname: Optional[str] = None
    path: Optional[str] = None
    capacity_tb: Optional[float] = None
    description: Optional[str] = None


class BackupSourceBase(BaseModel):
    server_id: int
    name: str
    type: str
    path: Optional[str] = None
    size_gb: Optional[float] = None
    description: Optional[str] = None


class BackupMethodBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


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
    status: str = 'active'
    notes: Optional[str] = None


app = FastAPI(title='BackupDocu API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '1.0.0', 'storage': 'json'}


@app.get('/api/topology')
def get_topology():
    return {
        'servers': load_collection('servers'),
        'sources': load_collection('sources'),
        'methods': load_collection('methods'),
        'targets': load_collection('targets'),
        'jobs': load_collection('jobs'),
    }


@app.get('/api/stats')
def get_stats():
    servers = load_collection('servers')
    sources = load_collection('sources')
    methods = load_collection('methods')
    targets = load_collection('targets')
    jobs = load_collection('jobs')
    return {
        'servers': len(servers),
        'sources': len(sources),
        'methods': len(methods),
        'targets': len(targets),
        'jobs': len(jobs),
        'jobs_active': len([j for j in jobs if j.get('status') == 'active']),
        'jobs_with_tape': len([j for j in jobs if j.get('tape_target_id')]),
        'jobs_with_offsite': len([j for j in jobs if j.get('offsite_target_id')]),
    }


def create_crud(collection: str, schema):

    @app.get(f'/api/{collection}')
    def list_items():
        return load_collection(collection)

    @app.get(f'/api/{collection}/{{item_id}}')
    def get_item_by_id(item_id: int):
        item = get_item(collection, item_id)
        if not item:
            raise HTTPException(status_code=404, detail='Not found')
        return item

    @app.post(f'/api/{collection}', status_code=201)
    def add(item: schema):
        return upsert_item(collection, None, item.model_dump())

    @app.put(f'/api/{collection}/{{item_id}}')
    def update(item_id: int, item: schema):
        return upsert_item(collection, item_id, item.model_dump())

    @app.delete(f'/api/{collection}/{{item_id}}', status_code=204)
    def remove(item_id: int):
        delete_item(collection, item_id)


create_crud('servers', ServerBase)
create_crud('sources', BackupSourceBase)
create_crud('methods', BackupMethodBase)
create_crud('targets', BackupTargetBase)
create_crud('jobs', BackupJobBase)
