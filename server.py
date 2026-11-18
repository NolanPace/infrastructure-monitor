"""Single-user local dashboard server. Do not expose directly to untrusted networks."""
import argparse,json,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from monitor import check,connect,record,latest,history,load_targets

HERE=Path(__file__).parent

def serve(targets,db_path,port,interval,allow_private):
    lock=threading.Lock();db=connect(db_path)
    def scan():
        for target in targets:
            result=check(target,allow_private)
            with lock:record(db,result)
            print(f'{result["name"]}: {"UP" if result["ok"] else "DOWN"} ({result["latency_ms"]} ms)',flush=True)
    def loop():
        while True:
            scan();time.sleep(interval)
    threading.Thread(target=loop,daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route=urlparse(self.path)
            if route.path=='/':
                payload=(HERE/'static/index.html').read_bytes();content_type='text/html; charset=utf-8'
            elif route.path=='/api/status':
                with lock:data=latest(db)
                payload=json.dumps(data).encode();content_type='application/json'
            elif route.path=='/api/history':
                args=parse_qs(route.query);name=args.get('name',[''])[0]
                with lock:data=history(db,name)
                payload=json.dumps(data).encode();content_type='application/json'
            elif route.path=='/healthz':
                payload=b'{"ok":true}';content_type='application/json'
            else:
                self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type',content_type)
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers();self.wfile.write(payload)
    http=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Local monitor: http://127.0.0.1:{port}')
    try:http.serve_forever()
    finally:http.server_close();db.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--targets',default=str(HERE/'targets.example.json'))
    p.add_argument('--db',default='checks.sqlite3')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--interval',type=int,default=30)
    p.add_argument('--allow-private',action='store_true',help='Allow operator-approved private/LAN targets')
    a=p.parse_args()
    if a.interval<5:p.error('interval must be >=5 seconds')
    serve(load_targets(a.targets),a.db,a.port,a.interval,a.allow_private)
if __name__=='__main__':main()
