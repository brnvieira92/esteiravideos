import json, subprocess
from pathlib import Path
import pytest
from tests.test_workflow import client, HEAD, post, setup_project, completed_result
from backend.core import DATA,db,probe


def reaction_file(tmp_path,audio=True,color='red',duration=3):
    path=tmp_path/('reaction-'+color+('-audio' if audio else '-silent')+'.mp4')
    cmd=['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=240x320:r=30:d={duration}']
    if audio: cmd+=['-f','lavfi','-i',f'sine=frequency=880:duration={duration}']
    subprocess.run(cmd+['-c:v','libx264','-threads','1','-c:a','aac','-y',str(path)],check=True)
    return path


def upload_reaction(pid,path,offset=0,recorded=False):
    r=client.post(f'/api/projects/{pid}/media?role=reaction&offset={offset}',content=path.read_bytes(),headers={**HEAD,'X-Video-Extension':path.suffix,**({'X-Recorded':'1'} if recorded else {})})
    assert r.status_code==200,r.text
    return r.json()


@pytest.mark.parametrize('base_audio,reaction_audio',[(True,True),(False,True),(True,False),(False,False)])
def test_two_sources_actual_pixels_audio_and_protected_originals(tmp_path,base_audio,reaction_audio):
    p,m,cut=setup_project(base_audio)
    r=upload_reaction(p['id'],reaction_file(tmp_path,reaction_audio),offset=-.1)
    cut.update(reactionId=r['id'],reactionOffset=-.1,baseVolume=.35,reactionVolume=1,cam=dict(x=0,y=0,w=1,h=1),split=.5)
    saved=post('/projects/'+p['id']+'/cuts',cut)
    jid=completed_result(p,saved,'two-sources-123456789')
    output=DATA/p['id']/(jid+'.mp4'); meta=probe(output)
    assert meta['audio']==(base_audio or reaction_audio)
    # Decode a pixel from the center of the upper half: it must come from the red reaction.
    pixel=subprocess.run(['ffmpeg','-v','error','-i',str(output),'-vf','crop=2:2:540:300,format=rgb24','-frames:v','1','-f','rawvideo','pipe:1'],capture_output=True,check=True).stdout
    assert pixel[0]>200 and pixel[1]<50 and pixel[2]<50
    with db() as c: snapshot=json.loads(c.execute('SELECT snapshot FROM jobs WHERE id=?',(jid,)).fetchone()[0])
    assert snapshot['reactionPath']!=snapshot['path']
    assert snapshot['reactionMeta']['width']==240
    assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==200
    assert client.get('/api/media/'+r['id']).status_code==200
    assert client.get('/api/media/'+m['id']).status_code==200


def test_reaction_scope_coverage_and_frozen_snapshot(tmp_path):
    p,m,cut=setup_project(); other,_,_=setup_project()
    r=upload_reaction(other['id'],reaction_file(tmp_path))
    assert client.post('/api/projects/'+p['id']+'/cuts',json={**cut,'reactionId':r['id']},headers=HEAD).status_code==422
    r=upload_reaction(p['id'],reaction_file(tmp_path))
    bad={**cut,'reactionId':r['id'],'reactionOffset':1}
    assert client.post('/api/projects/'+p['id']+'/cuts',json=bad,headers=HEAD).status_code==422
    good=post('/projects/'+p['id']+'/cuts',{**cut,'reactionId':r['id'],'reactionOffset':0})
    ids=post('/projects/'+p['id']+'/export',{'ids':[good['id']],'requestId':'frozen-react-123456789'})['ids']
    post('/projects/'+p['id']+'/cuts',{**good,'reactionOffset':-.1,'cam':dict(x=.2,y=.2,w=.5,h=.5)})
    with db() as c: snapshot=json.loads(c.execute('SELECT snapshot FROM jobs WHERE id=?',(ids[0],)).fetchone()[0])
    assert snapshot['reactionOffset']==0 and snapshot['cam']==cut['cam']
    post('/jobs/'+ids[0]+'/cancel',{})


def test_recorded_webm_is_seekable_and_raw_capture_is_kept(tmp_path):
    p,_,cut=setup_project(); path=tmp_path/'camera.webm'
    # WebM written to a pipe has no final duration index, as with browser MediaRecorder.
    with path.open('wb') as out:
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=320x180:r=24:d=2','-f','lavfi','-i','sine=d=2','-c:v','libvpx','-threads','1','-c:a','libopus','-f','webm','pipe:1'],stdout=out,check=True)
    r=upload_reaction(p['id'],path,recorded=True)
    assert abs(r['duration']-2)<.2
    assert (DATA/p['id']/(r['id']+'.original.webm')).read_bytes()==path.read_bytes()
    assert r['id'] in [v['id'] for v in client.get('/api/projects/'+p['id']).json()['reactions']]


@pytest.mark.parametrize('base_volume,reaction_volume,frequency',[(0,1,880),(1,0,440)])
def test_voice_and_base_volume_controls_act_on_export(tmp_path,base_volume,reaction_volume,frequency):
    import array
    p,_,cut=setup_project()
    r=upload_reaction(p['id'],reaction_file(tmp_path))
    cut.update(reactionId=r['id'],reactionOffset=0,baseVolume=base_volume,reactionVolume=reaction_volume)
    saved=post('/projects/'+p['id']+'/cuts',cut)
    jid=completed_result(p,saved,'volume-controls-123456789')
    raw=subprocess.run(['ffmpeg','-v','error','-i',str(DATA/p['id']/(jid+'.mp4')),'-vn','-ac','1','-ar','8000','-f','s16le','pipe:1'],capture_output=True,check=True).stdout
    samples=array.array('h');samples.frombytes(raw)
    samples=samples[800:-800]
    crossings=sum((a<0)!=(b<0) for a,b in zip(samples,samples[1:]))
    measured=crossings/2/(len(samples)/8000)
    assert abs(measured-frequency)<25


def test_database_v2_migrates_existing_originals_without_reset(tmp_path,monkeypatch):
    import sqlite3
    import backend.core as core
    target=tmp_path/'old-data';target.mkdir()
    c=sqlite3.connect(target/'esteira.db')
    c.executescript("CREATE TABLE media(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,path TEXT NOT NULL,meta TEXT NOT NULL); PRAGMA user_version=2;")
    c.execute('INSERT INTO media VALUES (?,?,?,?)',('original-id','project-id','original.mp4','{}'));c.commit();c.close()
    monkeypatch.setattr(core,'DATA',target)
    core.init()
    with core.db() as c:
        row=c.execute('SELECT * FROM media').fetchone()
        assert row['id']=='original-id' and row['role']=='base' and row['offset']==0
        assert c.execute('PRAGMA user_version').fetchone()[0]==3
    core.init() # repeatable migration


def test_reaction_audio_keeps_its_original_delay(tmp_path):
    import array
    path=tmp_path/'delayed-voice.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=240x320:r=30:d=3',
                    '-itsoffset','0.8','-f','lavfi','-i','sine=frequency=880:duration=2.2',
                    '-c:v','libx264','-threads','1','-c:a','aac','-y',str(path)],check=True)
    p,_,cut=setup_project()
    reaction=upload_reaction(p['id'],path)
    cut.update(reactionId=reaction['id'],reactionOffset=0,baseVolume=0,reactionVolume=1)
    saved=post('/projects/'+p['id']+'/cuts',cut)
    jid=completed_result(p,saved,'delayed-reaction-123456789')
    raw=subprocess.run(['ffmpeg','-v','error','-i',str(DATA/p['id']/(jid+'.mp4')),
                        '-vn','-ac','1','-ar','8000','-f','s16le','pipe:1'],capture_output=True,check=True).stdout
    values=array.array('h');values.frombytes(raw)
    assert sum(abs(v) for v in values[800:2400])/1600<50
    assert sum(abs(v) for v in values[6400:8000])/1600>1000
