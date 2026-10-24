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
    with pytest.raises(ValueError): validate_cut({'start':0,'end':2,'game':dict(x=.8,y=0,w=.5,h=1)},3)
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
