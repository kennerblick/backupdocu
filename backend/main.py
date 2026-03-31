from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import shutil

# ─────────────────────────────────────────────────────────────────────────────
# DATA DIRECTORY SETUP
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
SERVERS_DIR = DATA_DIR / 'servers'
SERVERS_DIR.mkdir(exist_ok=True)

GLOBAL_FILES = {
    'servers': DATA_DIR / 'servers.json',
    'methods': DATA_DIR / 'methods.json',
    'targets': DATA_DIR / 'targets.json',
    'settings': DATA_DIR / 'settings.json',
}

DEFAULT_SERVER_LOCATIONS = [
    {'id': 1, 'name': 'extern'},
    {'id': 2, 'name': 'gruenes Netz'},
    {'id': 3, 'name': 'gelbes Netz'},
    {'id': 4, 'name': 'virtuell'},
]

# Initialize global files
for name, path in GLOBAL_FILES.items():
    if not path.exists():
        if name == 'methods':
            path.write_text(json.dumps([
                {'id': 1, 'name': 'Veeam Agent', 'type': 'veeam-agent', 'description': 'Veeam Agent für Linux/Windows'},
                {'id': 2, 'name': 'Veeam Backup & Replication', 'type': 'veeam-br', 'description': 'Veeam Backup & Replication'},
                {'id': 3, 'name': 'rsync', 'type': 'rsync', 'description': 'rsync Backup'},
                {'id': 4, 'name': 'Bash Script', 'type': 'bash-script', 'description': 'Benutzerdefiniertes Bash-Skript'},
                {'id': 5, 'name': 'pg_dump', 'type': 'pg_dump', 'description': 'PostgreSQL Dump'},
                {'id': 6, 'name': 'Tape Job', 'type': 'tape-job', 'description': 'Tape Sicherung'},
            ], indent=2, ensure_ascii=False), encoding='utf-8')
        elif name == 'settings':
            path.write_text(json.dumps({
                'custom_methods': [],
                'server_functions': [],
                'server_locations': DEFAULT_SERVER_LOCATIONS,
            }, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            path.write_text('[]', encoding='utf-8')


# ─────────────────────────────────────────────────────────────────────────────
# DATA STORE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DataStore:
    """Manages data storage with per-server directories."""
    
    @staticmethod
    def load_global(name: str) -> List[Dict[str, Any]]:
        """Load global collection (servers, methods, targets, settings)."""
        path = GLOBAL_FILES.get(name)
        if not path:
            raise ValueError(f'Unknown global collection: {name}')
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    @staticmethod
    def save_global(name: str, data: List[Dict[str, Any]]) -> None:
        """Save global collection."""
        path = GLOBAL_FILES.get(name)
        if not path:
            raise ValueError(f'Unknown global collection: {name}')
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    @staticmethod
    def load_server_data(server_id: int, name: str) -> List[Dict[str, Any]]:
        """Load server-specific collection (sources or jobs)."""
        if name not in ['sources', 'jobs']:
            raise ValueError(f'Unknown server collection: {name}')
        
        server_dir = SERVERS_DIR / str(server_id)
        server_dir.mkdir(exist_ok=True)
        path = server_dir / f'{name}.json'
        
        if not path.exists():
            return []
        
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    @staticmethod
    def save_server_data(server_id: int, name: str, data: List[Dict[str, Any]]) -> None:
        """Save server-specific collection."""
        if name not in ['sources', 'jobs']:
            raise ValueError(f'Unknown server collection: {name}')
        
        server_dir = SERVERS_DIR / str(server_id)
        server_dir.mkdir(exist_ok=True)
        path = server_dir / f'{name}.json'
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    @staticmethod
    def delete_server_directory(server_id: int) -> None:
        """Delete entire server directory."""
        server_dir = SERVERS_DIR / str(server_id)
        if server_dir.exists():
            shutil.rmtree(server_dir)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def next_id(items: List[Dict[str, Any]]) -> int:
    """Generate next ID for collection."""
    return max((item.get('id', 0) for item in items), default=0) + 1


def get_item_global(collection: str, item_id: int) -> Optional[Dict[str, Any]]:
    """Get item from global collection."""
    items = DataStore.load_global(collection)
    for item in items:
        if item.get('id') == item_id:
            return item
    return None


def get_item_server(server_id: int, collection: str, item_id: int) -> Optional[Dict[str, Any]]:
    """Get item from server-specific collection."""
    items = DataStore.load_server_data(server_id, collection)
    for item in items:
        if item.get('id') == item_id:
            return item
    return None


def upsert_global(collection: str, item_id: Optional[int], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update item in global collection."""
    items = DataStore.load_global(collection)
    
    if item_id is None:
        payload['id'] = next_id(items)
        payload['created_at'] = datetime.utcnow().isoformat()
        payload['updated_at'] = datetime.utcnow().isoformat()
        items.append(payload)
        DataStore.save_global(collection, items)
        return payload
    
    existing = None
    for item in items:
        if item.get('id') == item_id:
            existing = item
            break
    if not existing:
        raise HTTPException(status_code=404, detail='Not found')

    for key, value in payload.items():
        existing[key] = value
    existing['updated_at'] = datetime.utcnow().isoformat()
    DataStore.save_global(collection, items)
    return existing


def upsert_server(server_id: int, collection: str, item_id: Optional[int], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update item in server-specific collection."""
    items = DataStore.load_server_data(server_id, collection)
    
    if item_id is None:
        payload['id'] = next_id(items)
        payload['created_at'] = datetime.utcnow().isoformat()
        payload['updated_at'] = datetime.utcnow().isoformat()
        items.append(payload)
        DataStore.save_server_data(server_id, collection, items)
        return payload
    
    existing = None
    for item in items:
        if item.get('id') == item_id:
            existing = item
            break
    if not existing:
        raise HTTPException(status_code=404, detail='Not found')

    for key, value in payload.items():
        existing[key] = value
    existing['updated_at'] = datetime.utcnow().isoformat()
    DataStore.save_server_data(server_id, collection, items)
    return existing


def delete_global(collection: str, item_id: int) -> None:
    """Delete item from global collection."""
    items = DataStore.load_global(collection)
    new_items = [item for item in items if item.get('id') != item_id]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail='Not found')
    DataStore.save_global(collection, new_items)


def delete_server(server_id: int, collection: str, item_id: int) -> None:
    """Delete item from server-specific collection."""
    items = DataStore.load_server_data(server_id, collection)
    new_items = [item for item in items if item.get('id') != item_id]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail='Not found')
    DataStore.save_server_data(server_id, collection, new_items)


def delete_server_with_data(server_id: int) -> None:
    """Delete server and all associated data."""
    delete_global('servers', server_id)
    DataStore.delete_server_directory(server_id)


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ServerBase(BaseModel):
    name: str
    hostname: Optional[str] = None
    type: Optional[str] = 'physical'
    os: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    functions: List[str] = []


class ServerFunction(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


class ServerLocation(BaseModel):
    id: Optional[int] = None
    name: str


class BackupSourceBase(BaseModel):
    name: str
    type: str
    path: Optional[str] = None
    size_gb: Optional[float] = None
    description: Optional[str] = None


class BackupTargetBase(BaseModel):
    name: str
    type: str
    hostname: Optional[str] = None
    path: Optional[str] = None
    capacity_tb: Optional[float] = None
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


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title='BackupDocu API', version='2.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: HEALTH & STATS
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '2.0.0', 'storage': 'json', 'architecture': 'per-server-directories'}


@app.get('/api/stats')
def get_stats():
    servers = DataStore.load_global('servers')
    targets = DataStore.load_global('targets')
    
    total_sources = 0
    total_jobs = 0
    jobs_active = 0
    jobs_with_tape = 0
    jobs_with_offsite = 0
    
    for server in servers:
        server_id = server.get('id')
        sources = DataStore.load_server_data(server_id, 'sources')
        jobs = DataStore.load_server_data(server_id, 'jobs')
        
        total_sources += len(sources)
        total_jobs += len(jobs)
        jobs_active += len([j for j in jobs if j.get('status') == 'active'])
        jobs_with_tape += len([j for j in jobs if j.get('tape_target_id')])
        jobs_with_offsite += len([j for j in jobs if j.get('offsite_target_id')])
    
    return {
        'servers': len(servers),
        'sources': total_sources,
        'methods': len(DataStore.load_global('methods')),
        'targets': len(targets),
        'jobs': total_jobs,
        'jobs_active': jobs_active,
        'jobs_with_tape': jobs_with_tape,
        'jobs_with_offsite': jobs_with_offsite,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: GLOBAL RESOURCES (Servers, Methods, Targets)
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/servers')
def list_servers():
    return DataStore.load_global('servers')


@app.get('/api/servers/{server_id}')
def get_server(server_id: int):
    server = get_item_global('servers', server_id)
    if not server:
        raise HTTPException(status_code=404, detail='Server not found')
    return server


@app.post('/api/servers', status_code=201)
def create_server(server: ServerBase):
    return upsert_global('servers', None, server.model_dump())


@app.put('/api/servers/{server_id}')
def update_server(server_id: int, server: ServerBase):
    return upsert_global('servers', server_id, server.model_dump())


@app.delete('/api/servers/{server_id}', status_code=204)
def delete_server_endpoint(server_id: int):
    delete_server_with_data(server_id)


@app.get('/api/methods')
def list_methods():
    return DataStore.load_global('methods')


@app.get('/api/methods/{method_id}')
def get_method(method_id: int):
    method = get_item_global('methods', method_id)
    if not method:
        raise HTTPException(status_code=404, detail='Method not found')
    return method


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: SERVER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/server-functions')
def list_server_functions():
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    return settings.get('server_functions', [])


@app.post('/api/server-functions', status_code=201)
def create_server_function(fn: ServerFunction):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    funcs = settings.get('server_functions', [])
    fn_dict = fn.model_dump()
    fn_dict['id'] = max((f.get('id', 0) for f in funcs), default=0) + 1
    funcs.append(fn_dict)
    settings['server_functions'] = funcs
    DataStore.save_global('settings', settings)
    return fn_dict


@app.put('/api/server-functions/{fn_id}')
def update_server_function(fn_id: int, fn: ServerFunction):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    funcs = settings.get('server_functions', [])
    for i, f in enumerate(funcs):
        if f.get('id') == fn_id:
            funcs[i] = {'id': fn_id, 'name': fn.name, 'description': fn.description}
            settings['server_functions'] = funcs
            DataStore.save_global('settings', settings)
            return funcs[i]
    raise HTTPException(status_code=404, detail='Server function not found')


@app.delete('/api/server-functions/{fn_id}', status_code=204)
def delete_server_function(fn_id: int):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    funcs = settings.get('server_functions', [])
    new_funcs = [f for f in funcs if f.get('id') != fn_id]
    if len(new_funcs) == len(funcs):
        raise HTTPException(status_code=404, detail='Server function not found')
    settings['server_functions'] = new_funcs
    DataStore.save_global('settings', settings)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: SERVER LOCATIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/server-locations')
def list_server_locations():
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    return settings.get('server_locations', DEFAULT_SERVER_LOCATIONS)


@app.post('/api/server-locations', status_code=201)
def create_server_location(location: ServerLocation):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    locations = settings.get('server_locations', DEFAULT_SERVER_LOCATIONS.copy())
    loc_dict = location.model_dump()
    loc_dict['id'] = max((l.get('id', 0) for l in locations), default=0) + 1
    locations.append(loc_dict)
    settings['server_locations'] = locations
    DataStore.save_global('settings', settings)
    return loc_dict


@app.put('/api/server-locations/{location_id}')
def update_server_location(location_id: int, location: ServerLocation):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    locations = settings.get('server_locations', DEFAULT_SERVER_LOCATIONS.copy())
    for i, l in enumerate(locations):
        if l.get('id') == location_id:
            locations[i] = {'id': location_id, 'name': location.name}
            settings['server_locations'] = locations
            DataStore.save_global('settings', settings)
            return locations[i]
    raise HTTPException(status_code=404, detail='Server location not found')


@app.delete('/api/server-locations/{location_id}', status_code=204)
def delete_server_location(location_id: int):
    settings = DataStore.load_global('settings')
    if isinstance(settings, list):
        settings = {}
    locations = settings.get('server_locations', DEFAULT_SERVER_LOCATIONS.copy())
    new_locations = [l for l in locations if l.get('id') != location_id]
    if len(new_locations) == len(locations):
        raise HTTPException(status_code=404, detail='Server location not found')
    settings['server_locations'] = new_locations
    DataStore.save_global('settings', settings)


@app.get('/api/targets')
def list_targets():
    return DataStore.load_global('targets')


@app.get('/api/targets/{target_id}')
def get_target(target_id: int):
    target = get_item_global('targets', target_id)
    if not target:
        raise HTTPException(status_code=404, detail='Target not found')
    return target


@app.post('/api/targets', status_code=201)
def create_target(target: BackupTargetBase):
    return upsert_global('targets', None, target.model_dump())


@app.put('/api/targets/{target_id}')
def update_target(target_id: int, target: BackupTargetBase):
    return upsert_global('targets', target_id, target.model_dump())


@app.delete('/api/targets/{target_id}', status_code=204)
def delete_target(target_id: int):
    delete_global('targets', target_id)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: SERVER-SPECIFIC RESOURCES (Sources, Jobs)
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/servers/{server_id}/sources')
def list_sources(server_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return DataStore.load_server_data(server_id, 'sources')


@app.get('/api/servers/{server_id}/sources/{source_id}')
def get_source(server_id: int, source_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    source = get_item_server(server_id, 'sources', source_id)
    if not source:
        raise HTTPException(status_code=404, detail='Source not found')
    return source


@app.post('/api/servers/{server_id}/sources', status_code=201)
def create_source(server_id: int, source: BackupSourceBase):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return upsert_server(server_id, 'sources', None, source.model_dump())


@app.put('/api/servers/{server_id}/sources/{source_id}')
def update_source(server_id: int, source_id: int, source: BackupSourceBase):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return upsert_server(server_id, 'sources', source_id, source.model_dump())


@app.delete('/api/servers/{server_id}/sources/{source_id}', status_code=204)
def delete_source(server_id: int, source_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    delete_server(server_id, 'sources', source_id)


@app.get('/api/servers/{server_id}/jobs')
def list_jobs(server_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return DataStore.load_server_data(server_id, 'jobs')


@app.get('/api/servers/{server_id}/jobs/{job_id}')
def get_job(server_id: int, job_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    job = get_item_server(server_id, 'jobs', job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@app.post('/api/servers/{server_id}/jobs', status_code=201)
def create_job(server_id: int, job: BackupJobBase):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return upsert_server(server_id, 'jobs', None, job.model_dump())


@app.put('/api/servers/{server_id}/jobs/{job_id}')
def update_job(server_id: int, job_id: int, job: BackupJobBase):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    return upsert_server(server_id, 'jobs', job_id, job.model_dump())


@app.delete('/api/servers/{server_id}/jobs/{job_id}', status_code=204)
def delete_job(server_id: int, job_id: int):
    if not get_item_global('servers', server_id):
        raise HTTPException(status_code=404, detail='Server not found')
    delete_server(server_id, 'jobs', job_id)


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY COMPATIBILITY
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/topology')
def get_topology():
    """Legacy endpoint - returns all data in old structure."""
    servers = DataStore.load_global('servers')
    all_sources = []
    all_jobs = []
    
    for server in servers:
        sid = server.get('id')
        sources = DataStore.load_server_data(sid, 'sources')
        jobs = DataStore.load_server_data(sid, 'jobs')
        all_sources.extend(sources)
        all_jobs.extend(jobs)
    
    return {
        'servers': servers,
        'sources': all_sources,
        'methods': DataStore.load_global('methods'),
        'targets': DataStore.load_global('targets'),
        'jobs': all_jobs,
    }
