"""Local HTTP health monitoring, SQLite history and opt-in polling."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
import ipaddress,json,sqlite3,time,socket

@dataclass(frozen=True)
class Target:
    name:str
    url:str
    timeout_s:float=3.0

def validate_target(t:Target,allow_private:bool=False):
    """Conservative endpoint validation for configured monitoring targets."""
    parsed=urlparse(t.url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only absolute HTTP(S) URLs without embedded credentials are allowed')
    if t.timeout_s<=0 or t.timeout_s>30:raise ValueError('Timeout must be between 0 and 30 seconds')
    if not allow_private:
        for info in socket.getaddrinfo(parsed.hostname,None):
            ip=ipaddress.ip_address(info[4][0])
            if not ip.is_global:raise ValueError('Non-public IP blocked; use --allow-private for trusted networks')

def check(t:Target,allow_private:bool=False)->dict:
    now=datetime.now(timezone.utc).isoformat()
    started=time.monotonic()
    try:
        validate_target(t,allow_private)
        # Target list is controlled by the local operator; redirects disabled to avoid surprises.
        from urllib.request import build_opener,HTTPRedirectHandler
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        try:
            with build_opener(NoRedirect).open(Request(t.url,headers={'User-Agent':'LocalInfrastructureMonitor/1.0'}),timeout=t.timeout_s) as resp:
                status=resp.status
        except HTTPError as err:
            status=err.code
        return {'name':t.name,'url':t.url,'timestamp':now,'ok':200<=status<400,'status':status,'latency_ms':round((time.monotonic()-started)*1000,1),'error':None}
    except (OSError,ValueError,URLError) as err:
        return {'name':t.name,'url':t.url,'timestamp':now,'ok':False,'status':None,'latency_ms':round((time.monotonic()-started)*1000,1),'error':str(err)[:240]}

def connect(database:str|Path):
    db=sqlite3.connect(str(database),check_same_thread=False)
    db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, timestamp TEXT NOT NULL, ok INTEGER NOT NULL, status INTEGER, latency_ms REAL, error TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_checks_name_time ON checks(name,id DESC)')
    db.commit()
    return db

def record(db,result:dict):
    db.execute('INSERT INTO checks(name,url,timestamp,ok,status,latency_ms,error) VALUES (?,?,?,?,?,?,?)',tuple(result.get(k) for k in ('name','url','timestamp','ok','status','latency_ms','error')))
    db.commit()

def latest(db):
    return [dict(r) for r in db.execute('SELECT checks.* FROM checks INNER JOIN (SELECT name,MAX(id) AS id FROM checks GROUP BY name) last ON checks.id=last.id ORDER BY checks.name')]

def history(db,name:str,limit:int=100):
    return [dict(r) for r in db.execute('SELECT * FROM checks WHERE name=? ORDER BY id DESC LIMIT ?',(name,max(1,min(limit,1000))))]

def load_targets(path:str|Path)->list[Target]:
    data=json.loads(Path(path).read_text())
    if not isinstance(data,list):raise ValueError('Targets file must be a JSON array')
    names=set();targets=[]
    for item in data:
        t=Target(**item)
        if not t.name or t.name in names:raise ValueError('Each target must have a unique nonempty name')
        names.add(t.name);targets.append(t)
