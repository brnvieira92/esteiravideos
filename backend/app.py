import asyncio, hashlib, hmac, io, secrets, shutil, time, zipfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .core import *

sessions={}; attempts={}; pairing=secrets.token_hex(3).upper(); pairing_expiry=time.time()+600
LAN=os.getenv('ESTEIRA_LAN')=='1'
upload_lock=asyncio.Lock()

@asynccontextmanager
async def lifespan(app):
    if LAN: print(f'Pareamento (válido por 10 minutos): {pairing}',flush=True)
    yield

app=FastAPI(title='EsteiraVídeos',lifespan=lifespan)

@app.middleware('http')
async def security(request,call_next):
    host=request.headers.get('host','')
    if request.method in ('POST','PATCH') and not request.url.path.endswith('/media'):
        try: size=int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'detail':'Tamanho inválido.'},400)
        if size>2*1024*1024: return JSONResponse({'detail':'Requisição excede 2 MB.'},413)
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if origin and origin not in ('http://'+host,'https://'+host): return JSONResponse({'detail':'Origem não autorizada.'},403)
        if request.headers.get('sec-fetch-site')=='cross-site': return JSONResponse({'detail':'Requisição entre sites recusada.'},403)
        if request.url.path.startswith('/api/') and request.headers.get('x-esteira')!='1': return JSONResponse({'detail':'Cabeçalho de proteção ausente.'},403)
    # Loopback mode refuses hostile DNS rebinding hostnames.
    if not LAN and host.split(':')[0] not in ('localhost','127.0.0.1','[','testserver'): return JSONResponse({'detail':'Host não permitido.'},403)
    if LAN and request.url.path.startswith('/api/') and request.url.path not in ('/api/pair','/api/session'):
        if sessions.get(request.cookies.get('esteira_session',''),0)<time.time(): return JSONResponse({'detail':'Pareamento necessário.'},401)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; img-src 'self' blob: data:; script-src 'self'; connect-src 'self'"
    return response

@app.exception_handler(ValueError)
async def value_error(request,e): return JSONResponse({'detail':str(e)},422)

def get(table,id):
    if table not in ('projects','media','cuts','jobs'): raise ValueError('Tabela inválida.')
    with db() as c: row=c.execute(f'SELECT * FROM {table} WHERE id=?',(id,)).fetchone()
    if not row: raise HTTPException(404,'Item não encontrado.')
    return dict(row)

def media_for(pid):
    get('projects',pid)
    with db() as c: m=c.execute('SELECT * FROM media WHERE project_id=?',(pid,)).fetchone()
    if not m: raise ValueError('Importe uma gravação primeiro.')
    return dict(m)

@app.get('/api/session')
def session(request:Request): return {'paired':not LAN or sessions.get(request.cookies.get('esteira_session',''),0)>time.time(),'lan':LAN}

@app.post('/api/pair')
async def pair(request:Request,response:Response):
    ip=request.client.host; now=time.time(); tries=[t for t in attempts.get(ip,[]) if t>now-60]; attempts[ip]=tries+[now]
    if len(tries)>=5: raise HTTPException(429,'Aguarde um minuto antes de tentar novamente.')
    body=await request.json()
    if now>pairing_expiry or not hmac.compare_digest(str(body.get('code','')).upper(),pairing): raise HTTPException(403,'Código incorreto ou expirado. Reinicie o servidor para gerar outro.')
    token=secrets.token_urlsafe(32); sessions[token]=now+86400
    response.set_cookie('esteira_session',token,httponly=True,samesite='strict',max_age=86400)
    return {'ok':True}

@app.get('/api/diagnostics')
def diagnostics():
    result={}
    for name,exe in [('ffmpeg',FFMPEG),('ffprobe',FFPROBE)]:
        try:
            r=subprocess.run([exe,'-version'],capture_output=True,text=True,timeout=10); result[name]=r.stdout.splitlines()[0]
        except (OSError,subprocess.SubprocessError): result[name]='Não encontrado'
    try:
        r=subprocess.run([FFMPEG,'-hide_banner','-filters'],capture_output=True,text=True,timeout=10); result['libass']=' subtitles ' in r.stdout
    except (OSError,subprocess.SubprocessError): result['libass']=False
    result.update(uploadGB=MAX_UPLOAD/1024**3,encoder='CPU / libx264',transcription='Não integrada nesta versão; edição manual e SRT disponíveis.')
    return result

@app.get('/api/projects')
def projects():
    with db() as c: return [dict(r) for r in c.execute('SELECT p.*, (SELECT count(*) FROM cuts WHERE project_id=p.id) AS cuts FROM projects p ORDER BY created DESC')]

@app.post('/api/projects')
async def create_project(request:Request):
    d=await request.json(); id=uid(); name=str(d.get('name','Novo projeto')).strip()[:150]
    if not name: raise ValueError('Informe um nome.')
    (DATA/id).mkdir()
    with db() as c: c.execute('INSERT INTO projects(id,name) VALUES (?,?)',(id,name))
    return get('projects',id)

@app.patch('/api/projects/{pid}')
async def rename(pid:str,request:Request):
    get('projects',pid); name=str((await request.json()).get('name','')).strip()[:150]
    if not name: raise ValueError('Nome vazio.')
    with db() as c: c.execute('UPDATE projects SET name=? WHERE id=?',(name,pid))
    return {'ok':True}

@app.delete('/api/projects/{pid}')
def delete_project(pid:str):
    get('projects',pid)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT 1 FROM jobs WHERE project_id=? AND (state IN ('aguardando','processando') OR running=1)",(pid,)).fetchone(): raise HTTPException(409,'Cancele as tarefas e aguarde o trabalhador antes de excluir.')
        for table in ('media','cuts','jobs','projects'): c.execute(f'DELETE FROM {table} WHERE '+('id' if table=='projects' else 'project_id')+'=?',(pid,))
    shutil.rmtree(DATA/pid,ignore_errors=True)
    return {'ok':True}

@app.post('/api/projects/{pid}/media')
async def upload(pid:str,request:Request):
    get('projects',pid)
    with db() as c:
        if c.execute('SELECT 1 FROM media WHERE project_id=?',(pid,)).fetchone(): raise HTTPException(409,'Cada projeto tem uma gravação. Crie outro projeto para importar outra.')
    suffix=request.headers.get('x-video-extension','').lower()
    if suffix not in ('.mp4','.mkv','.mov'): raise ValueError('Envie MP4, MKV ou MOV.')
    if upload_lock.locked(): raise HTTPException(429,'Aguarde o envio atual terminar.')
    await upload_lock.acquire()
    id=uid(); path=DATA/pid/(id+suffix); total=0
    try:
        with path.open('wb') as f:
            async for chunk in request.stream():
                total+=len(chunk)
                if total>MAX_UPLOAD: raise HTTPException(413,'Gravação excede o limite configurado.')
                f.write(chunk)
        meta=await asyncio.to_thread(probe,path)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM media WHERE project_id=?',(pid,)).fetchone(): raise HTTPException(409,'Já há uma gravação neste projeto.')
            c.execute('INSERT INTO media VALUES (?,?,?,?)',(id,pid,str(path),json.dumps(meta)))
    except Exception: path.unlink(missing_ok=True); raise
    finally: upload_lock.release()
    return {'id':id,**meta}

@app.get('/api/projects/{pid}')
def project(pid:str):
    p=get('projects',pid)
    with db() as c:
        m=c.execute('SELECT * FROM media WHERE project_id=?',(pid,)).fetchone()
        p['media']={'id':m['id'],**json.loads(m['meta'])} if m else None
        p['cuts']=[{'id':r['id'],**json.loads(r['data'])} for r in c.execute('SELECT * FROM cuts WHERE project_id=? ORDER BY rowid',(pid,))]
    return p

@app.post('/api/media/{mid}/proxy')
def make_proxy(mid:str):
    m=get('media',mid); meta=json.loads(m['meta'])
    d=validate_cut(dict(start=0,end=meta['duration'],name='Cópia de visualização'),meta['duration'])
    d.update(kind='proxy',media_id=mid,path=m['path'],meta=meta)
    with db() as c:
        for row in c.execute('SELECT id,snapshot,state FROM jobs WHERE project_id=?',(m['project_id'],)):
            old=json.loads(row['snapshot'])
            if old.get('kind')=='proxy' and old.get('media_id')==mid and row['state'] in ('aguardando','processando','concluído'): return {'id':row['id']}
        id=uid(); c.execute('INSERT INTO jobs(id,project_id,snapshot,title) VALUES (?,?,?,?)',(id,m['project_id'],json.dumps(d),'Cópia de visualização'))
    return {'id':id}

@app.get('/api/media/{mid}/proxy')
def read_proxy(mid:str):
    m=get('media',mid)
    with db() as c:
        for row in c.execute("SELECT * FROM jobs WHERE project_id=? AND state='concluído' ORDER BY created DESC",(m['project_id'],)):
            d=json.loads(row['snapshot'])
            if d.get('kind')=='proxy' and d.get('media_id')==mid: return FileResponse(row['output'],media_type='video/mp4')
    raise HTTPException(404,'Gere a cópia e aguarde a fila concluir.')

@app.get('/api/media/{mid}')
def video(mid:str): return FileResponse(get('media',mid)['path'])

@app.post('/api/projects/{pid}/cuts')
async def save_cut(pid:str,request:Request):
    m=media_for(pid); d=validate_cut(await request.json(),json.loads(m['meta'])['duration']); id=d.pop('id',None)
    if id and get('cuts',id)['project_id']!=pid: raise HTTPException(403)
    id=id or uid()
    with db() as c: c.execute('INSERT OR REPLACE INTO cuts VALUES (?,?,?)',(id,pid,json.dumps(d,ensure_ascii=False)))
    return {'id':id,**d}

@app.delete('/api/cuts/{cid}')
def delete_cut(cid:str):
    get('cuts',cid)
    with db() as c: c.execute('DELETE FROM cuts WHERE id=?',(cid,))
    return {'ok':True}

@app.post('/api/srt/parse')
async def import_srt(request:Request):
    d=await request.json(); text=d.get('text','')
    if len(text)>1000000: raise ValueError('SRT muito grande.')
    items=parse_srt(text)
    if d.get('source')=='recording': items=clipped_subtitles(items,float(d['start']),float(d['end']))
    return items

@app.post('/api/projects/{pid}/export')
async def export(pid:str,request:Request):
    m=media_for(pid); body=await request.json(); ids=body.get('ids',[])
    if not ids or len(ids)>100: raise ValueError('Selecione entre 1 e 100 cortes.')
    key=str(body.get('requestId',''))
    if not re.fullmatch('[a-zA-Z0-9-]{16,80}',key): raise ValueError('Identificador de requisição inválido.')
    jobs=[]
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        for index,cid in enumerate(dict.fromkeys(ids)):
            cut=get('cuts',cid)
            if cut['project_id']!=pid: raise HTTPException(403)
            d=validate_cut(json.loads(cut['data']),json.loads(m['meta'])['duration']); d.update(path=m['path'],meta=json.loads(m['meta']))
            if body.get('preview'): d['end']=min(d['end'],d['start']+5); d['subtitles']=clipped_subtitles(d.get('subtitles',[]),0,d['end']-d['start'])
            jid=hashlib.sha256((pid+key+str(index)).encode()).hexdigest()[:32]
            c.execute('INSERT OR IGNORE INTO jobs(id,project_id,snapshot,title) VALUES (?,?,?,?)',(jid,pid,json.dumps(d),d['name']))
            jobs.append(jid)
    return {'ids':jobs}

@app.get('/api/jobs')
def jobs():
    with db() as c: return [{k:r[k] for k in ('id','project_id','state','progress','error','reviewed','title','description','created')} | {'kind':json.loads(r['snapshot']).get('kind','export')} for r in c.execute('SELECT * FROM jobs ORDER BY created DESC,rowid DESC')]

@app.post('/api/jobs/{jid}/{action}')
def job_action(jid:str,action:str):
    j=get('jobs',jid)
    with db() as c:
        if action=='cancel' and j['state'] in ('aguardando','processando'): c.execute("UPDATE jobs SET state='cancelado' WHERE id=?",(jid,))
        elif action=='retry' and j['state'] in ('cancelado','falhou'):
            new=uid(); c.execute('INSERT INTO jobs(id,project_id,snapshot,title,description) VALUES (?,?,?,?,?)',(new,j['project_id'],j['snapshot'],j['title'],j['description']))
        else: raise HTTPException(409,'Ação indisponível neste estado.')
    return {'ok':True}

@app.patch('/api/jobs/{jid}')
async def edit_result(jid:str,request:Request):
    get('jobs',jid); d=await request.json()
    with db() as c: c.execute('UPDATE jobs SET title=?,description=?,reviewed=? WHERE id=?',(str(d.get('title',''))[:150],str(d.get('description',''))[:5000],bool(d.get('reviewed')),jid))
    return {'ok':True}

@app.get('/api/jobs/{jid}/file/{kind}')
def result_file(jid:str,kind:str,download:bool=False):
    j=get('jobs',jid)
    if kind=='thumbnail' and j['state']=='concluído':
        path=DATA/j['project_id']/(jid+'.jpg')
        if not path.exists(): raise HTTPException(404)
        return FileResponse(path,media_type='image/jpeg')
    if kind=='log': return FileResponse(DATA/j['project_id']/(jid+'.log'),media_type='text/plain')
    if j['state']!='concluído': raise HTTPException(409,'Resultado ainda não disponível.')
    path=Path(j['output']) if kind=='mp4' else DATA/j['project_id']/(jid+'.srt') if kind=='srt' else None
    if path is None: raise HTTPException(404)
    name=re.sub(r'[^\w -]','',j['title'])[:80] or 'corte'
    return FileResponse(path,filename=f'{name}-{jid[:6]}.{kind}' if download else None,media_type='video/mp4' if kind=='mp4' else 'application/x-subrip')

@app.post('/api/results/zip')
async def results_zip(request:Request):
    import tempfile
    ids=(await request.json()).get('ids',[])
    if not ids or len(ids)>100: raise ValueError('Selecione até 100 resultados.')
    f=tempfile.TemporaryFile()
    def prepare():
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
            for jid in dict.fromkeys(ids):
                j=get('jobs',jid)
                if j['state']!='concluído': raise ValueError('Há resultados não concluídos.')
                name=re.sub(r'[^\w -]','',j['title'])[:80] or 'corte'
                for ext in ('mp4','srt'): z.write(DATA/j['project_id']/(jid+'.'+ext),f'{name}-{jid[:6]}.{ext}')
        f.seek(0)
    try: await asyncio.to_thread(prepare)
    except Exception: f.close(); raise
    def chunks():
        try:
            while b:=f.read(1024*1024): yield b
        finally: f.close()
    return StreamingResponse(chunks(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="esteira-videos-resultados.zip"'})

from .resources import resource_root
DIST=resource_root()/'frontend'/'dist'
if DIST.exists(): app.mount('/',StaticFiles(directory=DIST,html=True),name='frontend')
