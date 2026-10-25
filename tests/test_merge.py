import pytest
import json
import subprocess
from tests.test_workflow import client,HEAD,post
from backend.core import DATA,db,uid,probe
from backend.worker import run_job


@pytest.mark.parametrize('subtitles',[True,False])
def test_merge_order_silence_subtitles_and_dependencies(subtitles):
    p=post('/projects',{'name':'Montagem'});pid=p['id'];ids=[]
    for color,audio in [('red',True),('blue',False)]:
        jid=uid();ids.append(jid);path=DATA/pid/(jid+'.mp4')
        cmd=['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=180x320:r=30:d=0.6']
        if audio:cmd+=['-f','lavfi','-i','sine=frequency=440:duration=0.6']
        subprocess.run(cmd+['-c:v','libx264','-threads','1','-c:a','aac','-y',str(path)],check=True)
        path.with_suffix('.srt').write_text('1\n00:00:00,100 --> 00:00:00,300\nOlá\n' if subtitles else '',encoding='utf-8')
        with db() as c:c.execute("INSERT INTO jobs(id,project_id,snapshot,title,state,output) VALUES (?,?,?,?,'concluído',?)",(jid,pid,json.dumps({'kind':'export'}),color,str(path)))
    result=post('/results/merge',{'ids':ids,'title':'Tudo junto'})
    assert post('/results/merge',{'ids':ids})['id']==result['id']
    assert client.delete('/api/jobs/'+ids[0],headers=HEAD).status_code==409
    assert client.delete('/api/projects/'+pid,headers=HEAD).status_code==409
    with db() as c:j=dict(c.execute('SELECT * FROM jobs WHERE id=?',(result['id'],)).fetchone())
    if subtitles: assert json.loads(j['snapshot'])['subtitles'][1]['start']>.6
    else: assert json.loads(j['snapshot'])['subtitles']==[]
    run_job(j)
    with db() as c:finished=dict(c.execute('SELECT * FROM jobs WHERE id=?',(j['id'],)).fetchone())
    assert finished['state']=='concluído',finished['error']
    meta=probe(finished['output']);assert abs(meta['duration']-1.2)<.15
    assert (meta['width'],meta['height'])==(1080,1920) and meta['audio']
    for time,color in [(.2,0),(.9,2)]:
        raw=subprocess.run(['ffmpeg','-v','error','-ss',str(time),'-i',finished['output'],'-frames:v','1','-vf','format=rgb24','-f','rawvideo','pipe:1'],capture_output=True,check=True).stdout
        pixel=raw[(800*1080+500)*3:][:3];assert pixel[color]>200 and pixel[2-color]<40
    reverse=post('/results/merge',{'ids':ids[::-1]});assert reverse['id']!=result['id']
    assert client.post('/api/results/merge',headers=HEAD,json={'ids':[ids[0],ids[0]]}).status_code==422
    assert client.post('/api/results/merge',headers=HEAD,json={'ids':[ids[0],'missing']}).status_code==422
    assert all((DATA/pid/(i+'.mp4')).is_file() for i in ids)
    post('/jobs/'+reverse['id']+'/cancel',{})
    assert client.delete('/api/jobs/'+ids[0],headers=HEAD).status_code==200
