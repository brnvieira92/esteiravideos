import array
import math
import subprocess
import pytest
from tests.test_workflow import client,HEAD,post,setup_project,completed_result
from backend.core import probe,DATA


@pytest.mark.parametrize('extension,codec',[('webm','libopus'),('mp4','aac')])
def test_audio_only_narration_render_and_gains(tmp_path,extension,codec):
    p,_,_=setup_project();audio=tmp_path/('voice.'+extension)
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=880:duration=1.5','-c:a',codec,'-y',str(audio)],check=True)
    with pytest.raises(ValueError):probe(audio)
    meta=probe(audio,allow_audio=True);assert meta['audioOnly'] and meta['width']==0
    r=client.post('/api/projects/'+p['id']+'/media?role=reaction&offset=0.2',content=audio.read_bytes(),headers={**HEAD,'X-Video-Extension':'.'+extension,'X-Recorded':'1'})
    assert r.status_code==200,r.text
    reaction=r.json();assert reaction['audioOnly'] and reaction['audio']
    assert client.get('/api/projects/'+p['id']).json()['reactions'][0]['audioOnly']
    assert client.post('/api/media/'+reaction['id']+'/proxy',headers=HEAD).status_code==422
    d=dict(name='Narração',start=.3,end=1.3,layout='gameplay',reactionId=reaction['id'],reactionOffset=.2,baseVolume=0,reactionVolume=1)
    for layout in ['combined','webcam']:
        assert client.post('/api/projects/'+p['id']+'/cuts',headers=HEAD,json={**d,'layout':layout}).status_code==422
    cut=post('/projects/'+p['id']+'/cuts',d);jid=completed_result(p,cut,'narration-render-123456')
    path=DATA/p['id']/(jid+'.mp4');result=probe(path)
    assert (result['width'],result['height'])==(1080,1920) and abs(result['duration']-1)<.15
    pcm=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','pipe:1'],capture_output=True,check=True).stdout
    samples=array.array('h',pcm)[800:-800]
    def amplitude(f):return math.hypot(sum(v*math.sin(2*math.pi*f*i/8000) for i,v in enumerate(samples)),sum(v*math.cos(2*math.pi*f*i/8000) for i,v in enumerate(samples)))
    assert amplitude(880)>10000 and amplitude(440)<amplitude(880)*.03
    changed=post('/projects/'+p['id']+'/cuts',{**cut,'reactionVolume':.5})
    queued=post('/projects/'+p['id']+'/export',{'ids':[changed['id']],'requestId':'narration-gain-123456'})
    assert queued['created']==1
    post('/jobs/'+queued['ids'][0]+'/cancel',{})
    fresh=post('/projects',{'name':'Base exige vídeo'})
    bad=client.post('/api/projects/'+fresh['id']+'/media',content=audio.read_bytes(),headers={**HEAD,'X-Video-Extension':'.'+extension,'X-Recorded':'1'})
    assert bad.status_code==422
