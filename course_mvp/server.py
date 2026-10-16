"""Local-only, bounded Blender regeneration server. Python standard library only."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, os, shutil, subprocess, threading, time, uuid
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
BLENDER = os.environ.get('TREESTRUCT3D_BLENDER') or next((str(p) for p in [REPO/'tools/Blender-5.0.app/Contents/MacOS/Blender',Path('/Applications/Blender.app/Contents/MacOS/Blender')] if p.exists()),None) or shutil.which('blender')
LOCK = threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(REPO),**kw)
    def do_GET(self):
        from urllib.parse import urlsplit, unquote
        path = unquote(urlsplit(self.path).path)
        allowed = path.startswith('/course_mvp/') or path.startswith('/visual_validation/frontend/vendor/')
        if not allowed or '..' in path.split('/'):
            self.send_error(404); return
        if path.startswith('/course_mvp/') and path.endswith(('.py', '.jsonl')):
            self.send_error(404); return
        super().do_GET()
    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://127.0.0.1:8876', 'http://localhost:8876'):
            self.send_error(403); return
        if self.path in ('/api/demo', '/api/performance'):
            length = int(self.headers.get('Content-Length', 0))
            maximum = 200_000_000 if self.path == '/api/demo' else 100_000
            if not 0 < length <= maximum:
                self.send_error(400); return
            payload = self.rfile.read(length)
            destination = ROOT/'evidence'
            destination.mkdir(exist_ok=True)
            name = 'demo.webm' if self.path == '/api/demo' else 'viewport-performance.json'
            (destination/name).write_bytes(payload)
            body = json.dumps({'saved': '/course_mvp/evidence/'+name}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        if self.path != '/api/regenerate': self.send_error(404); return
        if not LOCK.acquire(blocking=False): self.send_error(409,'Blender is busy'); return
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0 < length <= 1024: raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            width=float(data['width'])
            if not .5 <= width <= 2: raise ValueError('Width must be between 0.5 and 2.0')
            if not BLENDER: raise RuntimeError('Blender not found; set TREESTRUCT3D_BLENDER')
            identifier=uuid.uuid4().hex
            out=ROOT/'runs'/identifier
            start=time.perf_counter()
            result=subprocess.run([BLENDER,'--background','--factory-startup','--python',str(ROOT/'chair.py'),'--',str(width),'1' if data.get('broken') else '0',str(out)],capture_output=True,text=True,timeout=60)
            if result.returncode or not (out/'validation.json').exists(): raise RuntimeError(result.stderr[-1500:] or result.stdout[-1500:])
            payload=json.loads((out/'validation.json').read_text())
            payload.update(latency_seconds=time.perf_counter()-start,glb=f'/course_mvp/runs/{identifier}/chair.glb')
            with (ROOT/'measurements.jsonl').open('a') as f: f.write(json.dumps(payload)+'\n')
            body=json.dumps(payload).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        except (ValueError,KeyError,json.JSONDecodeError) as e: self.send_error(400,str(e))
        except Exception as e: self.send_error(500,str(e))
        finally: LOCK.release()
if __name__=='__main__':
    print('TreeStruct3D course MVP: http://127.0.0.1:8876/course_mvp/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8876),Handler).serve_forever()
