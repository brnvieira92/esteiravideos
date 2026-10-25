import os, tempfile, subprocess, json, time, sys, io, zipfile
from pathlib import Path
os.environ['ESTEIRA_DATA']=tempfile.mkdtemp(prefix='esteira-videos-tests-')
from fastapi.testclient import TestClient
from backend.app import app
from backend.core import DATA, db, validate_cut, parse_srt, clipped_subtitles, geometry, probe
from backend.worker import run_job
import pytest
client=TestClient(app)
HEAD={'X-Esteira':'1'}

def post(path,body):
    r=client.post('/api'+path,json=body,headers=HEAD)
    assert r.status_code==200,r.text
    return r.json()

def sample(path,audio=True,duration=2):
    cmd=['ffmpeg','-v','error','-f','lavfi','-i',f'testsrc2=size=320x180:rate=24:duration={duration}']
    if audio: cmd+=['-f','lavfi','-i',f'sine=frequency=440:duration={duration}']
    subprocess.run(cmd+['-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-c:a','aac','-y',str(path)],check=True)

def setup_project(audio=True):
    p=post('/projects',{'name':'Teste português çã'})
    src=DATA/f'sample-{p["id"]}.mp4'; sample(src,audio)
    with src.open('rb') as f:
        r=client.post('/api/projects/'+p['id']+'/media',content=f.read(),headers={**HEAD,'X-Video-Extension':'.mp4'})
    assert r.status_code==200,r.text
    cut=post('/projects/'+p['id']+'/cuts',dict(name='O plano deu errado',start=.2,end=1.5,layout='combined',game=dict(x=0,y=0,w=1,h=1),cam=dict(x=0,y=0,w=.5,h=.5),subtitles=[dict(start=0,end=1,text='Ação! Português çã')]))
    return p,r.json(),cut

def test_validation_and_subtitles():
    with pytest.raises(ValueError): validate_cut({'start':2,'end':1},3)
    adjusted=validate_cut({'start':0,'end':2,'game':dict(x=.8,y=0,w=.5,h=1)},3)
    assert adjusted['game']['x']==.5
    items=parse_srt('1\n00:00:01,250 --> 00:00:03,000\nOlá!\n')
    assert clipped_subtitles(items,2,4)==[dict(start=0,end=1,text='Olá!')]
    assert 'crop=320:180:0:0' in geometry(validate_cut({'start':0,'end':1},2),dict(width=320,height=180))

@pytest.mark.parametrize('audio',[True,False])
def test_end_to_end(audio):
    p,m,c=setup_project(audio)
    assert m['audio']==audio
    r=client.get('/api/media/'+m['id'],headers={'Range':'bytes=0-63'})
    assert r.status_code==206 and len(r.content)==64
    body=dict(ids=[c['id']],requestId='idempotency-test-12345')
    ids=post('/projects/'+p['id']+'/export',body)['ids']
    assert post('/projects/'+p['id']+'/export',body)['ids']==ids
    with db() as conn:
        j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(ids[0],)).fetchone())
        conn.execute("UPDATE jobs SET state='processando' WHERE id=?",(ids[0],))
    run_job(j)
    with db() as conn: result=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(ids[0],)).fetchone())
    assert result['state']=='concluído',result
    meta=probe(result['output'])
    assert (meta['width'],meta['height'])==(1080,1920)
    assert abs(meta['duration']-1.3)<.15
    assert meta['audio']==audio
    assert meta['fps']==30
    assert client.get('/api/jobs/'+ids[0]+'/file/mp4').status_code==200
    assert 'Português' in client.get('/api/jobs/'+ids[0]+'/file/srt').text
    z=client.post('/api/results/zip',json={'ids':ids},headers=HEAD)
    names=zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert len(names)==2 and all('original' not in n for n in names)
    assert client.get('/api/media/../../README.md').status_code!=200
    assert client.post('/api/projects',json={'name':'CSRF'}).status_code==403
    assert client.post('/api/projects',json={'name':'CSRF'},headers={**HEAD,'Origin':'http://evil.example'}).status_code==403

def test_cancel_and_recovery():
    p,m,c=setup_project()
    jid=post('/projects/'+p['id']+'/export',dict(ids=[c['id']],requestId='cancel-test-123456'))['ids'][0]
    post('/jobs/'+jid+'/cancel',{})
    with db() as conn: j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    run_job(j)
    assert not (DATA/p['id']/(jid+'.partial.mp4')).exists()
    with db() as conn:
        assert conn.execute('SELECT state FROM jobs WHERE id=?',(jid,)).fetchone()[0]=='cancelado'
        conn.execute("UPDATE jobs SET state='processando' WHERE id=?",(jid,))
    proc=subprocess.Popen([sys.executable,'-m','backend.worker'])
    try:
        time.sleep(1)
        with db() as conn:
            r=conn.execute('SELECT state,error FROM jobs WHERE id=?',(jid,)).fetchone()
        assert r['state']=='falhou' and 'interrompido' in r['error']
        second=subprocess.run([sys.executable,'-m','backend.worker'],capture_output=True,timeout=5)
        assert second.returncode!=0
    finally: proc.terminate(); proc.wait(timeout=8)

def test_network_pairing():
    import backend.app as module
    old=module.LAN; module.LAN=True
    try:
        with TestClient(app) as other:
            assert other.get('/api/projects').status_code==401
            assert other.delete('/api/jobs/unknown',headers=HEAD).status_code==401
            assert other.post('/api/pair',json={'code':'WRONG'},headers=HEAD).status_code==403
            r=other.post('/api/pair',json={'code':module.pairing},headers=HEAD)
            assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
            assert other.get('/api/projects').status_code==200
    finally: module.LAN=old

def test_proxy_and_running_cancel():
    p,m,c=setup_project()
    jid=post('/media/'+m['id']+'/proxy',{})['id']
    with db() as conn: j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    run_job(j)
    result=client.get('/api/media/'+m['id']+'/proxy')
    assert result.status_code==200
    with db() as conn:
        output=conn.execute('SELECT output FROM jobs WHERE id=?',(jid,)).fetchone()[0]
    meta=probe(output)
    assert (meta['width'],meta['height'])==(320,180) and abs(meta['duration']-2)<.1
    # A long output makes cancellation happen during encoding, not before launch.
    source=DATA/'long-source.mp4'; sample(source,duration=20)
    with db() as conn:
        conn.execute('UPDATE media SET path=?,meta=? WHERE id=?',(str(source),json.dumps(probe(source)),m['id']))
    c['end']=19; c['subtitles']=[]
    c=post('/projects/'+p['id']+'/cuts',c)
    jid=post('/projects/'+p['id']+'/export',dict(ids=[c['id']],requestId='live-cancel-123456789'))['ids'][0]
    proc=subprocess.Popen([sys.executable,'-m','backend.worker'])
    try:
        deadline=time.time()+10
        while time.time()<deadline:
            with db() as conn: row=conn.execute('SELECT state,running FROM jobs WHERE id=?',(jid,)).fetchone()
            if row['state']=='processando': break
            time.sleep(.1)
        assert row['state']=='processando'
        time.sleep(.3)
        post('/jobs/'+jid+'/cancel',{})
        deadline=time.time()+8
        while time.time()<deadline:
            with db() as conn: row=conn.execute('SELECT state,running FROM jobs WHERE id=?',(jid,)).fetchone()
            if not row['running']: break
            time.sleep(.1)
        assert row['state']=='cancelado' and row['running']==0
        assert not (DATA/p['id']/(jid+'.partial.mp4')).exists()
        assert not (DATA/p['id']/(jid+'.mp4')).exists()
    finally: proc.terminate(); proc.wait(timeout=8)


def test_invalid_upload_and_project_isolation():
    p=post('/projects',{'name':'Inválido'})
    r=client.post('/api/projects/'+p['id']+'/media',content=b'not a video',headers={**HEAD,'X-Video-Extension':'.mp4'})
    assert r.status_code==422
    assert not list((DATA/p['id']).iterdir())
    assert client.get('/api/media/not-an-internal-id').status_code==404
    p1,m,c=setup_project()
    r=client.post('/api/projects/'+p['id']+'/export',json={'ids':[c['id']],'requestId':'different-project-1234'},headers=HEAD)
    assert r.status_code==422  # target has no media; never gains access to another project


def test_screenshot_region_adjustment_persists_and_exports():
    from backend.core import normalize_box
    raw=dict(x=.06,y=.35,w=.62,h=.87)
    normalized=normalize_box(raw)
    assert normalized['y']==pytest.approx(.13)
    assert normalized['h']==.87
    assert normalize_box(normalized)==normalized
    d=validate_cut(dict(start=0,end=1,game=raw,cam=dict(x=.69,y=.51,w=.31,h=.27)),2)
    assert 'crop=1190:938:114:140' in geometry(d,dict(width=1920,height=1080))
    for invalid in (dict(x=0,y=0,w=0,h=1),dict(x=-.1,y=0,w=1,h=1),
                    dict(x=0,y=float('nan'),w=1,h=1),dict(x=0,y=0,w=1,h=1.1)):
        with pytest.raises(ValueError): normalize_box(invalid)
    p,m,cut=setup_project()
    cut.update(game=raw,cam=dict(x=.69,y=.51,w=.31,h=.27),split=.48)
    saved=post('/projects/'+p['id']+'/cuts',cut)
    persisted=client.get('/api/projects/'+p['id']).json()['cuts'][0]
    assert saved['game']==persisted['game']==normalized
    jid=post('/projects/'+p['id']+'/export',dict(ids=[saved['id']],requestId='adjusted-region-test-1234'))['ids'][0]
    with db() as conn: j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    assert json.loads(j['snapshot'])['game']==normalized
    run_job(j)
    with db() as conn:
        result=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    assert result['state']=='concluído',result['error']
    assert probe(result['output'])['height']==1920


def completed_result(p,cut,key):
    jid=post('/projects/'+p['id']+'/export',dict(ids=[cut['id']],requestId=key))['ids'][0]
    with db() as conn: j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    run_job(j)
    with db() as conn:
        j=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    assert j['state']=='concluído',j['error']
    return jid


def test_delete_result_removes_only_generated_files_and_retains_idempotency():
    p,m,cut=setup_project()
    key='delete-result-12345678'
    jid=completed_result(p,cut,key)
    folder=DATA/p['id']
    with db() as conn: original=Path(conn.execute('SELECT path FROM media WHERE id=?',(m['id'],)).fetchone()[0])
    original_bytes=original.read_bytes()
    assert (folder/(jid+'.mp4')).exists() and (folder/(jid+'.srt')).exists()
    response=client.delete('/api/jobs/'+jid,headers=HEAD)
    assert response.status_code==200,response.text
    assert all(not (folder/(jid+ext)).exists() for ext in ('.mp4','.srt','.ass','.jpg','.log','.partial.mp4'))
    assert original.read_bytes()==original_bytes
    project=client.get('/api/projects/'+p['id']).json()
    assert project['media']['id']==m['id'] and project['cuts'][0]['id']==cut['id']
    assert all(j['id']!=jid for j in client.get('/api/jobs').json())
    assert client.get('/api/jobs/'+jid+'/file/mp4').status_code==410
    assert client.patch('/api/jobs/'+jid,json={'title':'stale review'},headers=HEAD).status_code==410
    assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==200
    assert post('/projects/'+p['id']+'/export',dict(ids=[cut['id']],requestId=key))['ids']==[jid]
    with db() as conn: assert conn.execute('SELECT state FROM jobs WHERE id=?',(jid,)).fetchone()[0]=='excluído'
    # A new export remains available, using the saved cut and preserved original.
    new=post('/projects/'+p['id']+'/export',dict(ids=[cut['id']],requestId='new-after-deletion-12345',force=True))['ids'][0]
    assert new!=jid
    post('/jobs/'+new+'/cancel',{})


def test_delete_result_rejects_running_and_locked_files(monkeypatch):
    p,m,cut=setup_project()
    jid=completed_result(p,cut,'locked-delete-result-1234')
    mp4=DATA/p['id']/(jid+'.mp4')
    with db() as conn: conn.execute('UPDATE jobs SET running=1 WHERE id=?',(jid,))
    assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==409
    assert mp4.exists()
    with db() as conn: conn.execute('UPDATE jobs SET running=0 WHERE id=?',(jid,))
    original_unlink=Path.unlink
    def locked(path,*args,**kwargs):
        if path==mp4: raise PermissionError('Simulated Windows open video handle')
        return original_unlink(path,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'unlink',locked)
        assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==409
        assert mp4.exists() and mp4.with_suffix('.srt').exists()
    assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==200


def test_delete_result_protects_original_even_with_corrupt_job_metadata():
    p,m,cut=setup_project()
    with db() as conn:
        original=conn.execute('SELECT path FROM media WHERE id=?',(m['id'],)).fetchone()[0]
        conn.execute("INSERT INTO jobs(id,project_id,snapshot,state,output,title) VALUES (?,?,?,'concluído',?,?)",
                     (m['id'],p['id'],json.dumps(cut),original,'Must not delete original'))
    assert client.delete('/api/jobs/'+m['id'],headers=HEAD).status_code==409
    assert Path(original).exists()
    proxy=post('/media/'+m['id']+'/proxy',{})['id']
    with db() as conn: conn.execute("UPDATE jobs SET state='concluído' WHERE id=?",(proxy,))
    assert client.delete('/api/jobs/'+proxy,headers=HEAD).status_code==409
    assert client.delete('/api/jobs/not-an-internal-id',headers=HEAD).status_code==404


def test_cut_without_subtitles_has_a_complete_editor_payload():
    p,m,cut=setup_project()
    cut.pop('subtitles')
    saved=post('/projects/'+p['id']+'/cuts',cut)
    assert saved['subtitles']==[]
    # Old local records created without optional blocks still reopen in the editor.
    with db() as conn:
        legacy=dict(saved); legacy.pop('subtitles'); legacy.pop('id')
        conn.execute('UPDATE cuts SET data=? WHERE id=?',(json.dumps(legacy),saved['id']))
    reopened=client.get('/api/projects/'+p['id']).json()['cuts'][0]
    assert reopened['subtitles']==[]
