import array
import math
import subprocess
import pytest
from tests.test_workflow import client,HEAD,post,completed_result
from backend.core import DATA,probe


def source(path,left,right,frequency):
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color={left}:s=320x180:r=24:d=1.5,drawbox=x=160:y=0:w=160:h=180:color={right}:t=fill',
                    '-f','lavfi','-i',f'sine=frequency={frequency}:duration=1.5','-c:v','libx264','-threads','1','-c:a','aac','-y',str(path)],check=True)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mirror',[False,True])
def test_full_webcam_pixels_audio_and_export_identity(tmp_path,separate,mirror):
    base=tmp_path/'base.mp4';reaction=tmp_path/'reaction.mp4'
    source(base,'red','blue',440);source(reaction,'lime','yellow',880)
    p=post('/projects',{'name':'Opinião individual'})
    def upload(path,role):
        r=client.post('/api/projects/'+p['id']+'/media?role='+role,content=path.read_bytes(),headers={**HEAD,'X-Video-Extension':'.mp4'})
        assert r.status_code==200,r.text
        return r.json()
    upload(base,'base');r=upload(reaction,'reaction') if separate else None
    d=dict(start=.1,end=.9,layout='webcam',camFlip=mirror,cam=dict(x=0,y=0,w=1,h=1),game=dict(x=0,y=0,w=.3,h=.3),baseVolume=1,reactionVolume=1)
    if r:d.update(reactionId=r['id'],reactionOffset=0)
    cut=post('/projects/'+p['id']+'/cuts',d)
    jid=completed_result(p,cut,'full-camera-render-1234567')
    output=DATA/p['id']/(jid+'.mp4');m=probe(output)
    assert (m['width'],m['height'])==(1080,1920) and m['audio']
    pixels=subprocess.run(['ffmpeg','-v','error','-i',str(output),'-vf','format=rgb24','-frames:v','1','-f','rawvideo','pipe:1'],capture_output=True,check=True).stdout
    def pixel(x,y):i=(y*1080+x)*3;return tuple(pixels[i:i+3])
    for y in [300,1500]:
        left,right=pixel(270,y),pixel(810,y)
        if mirror:left,right=right,left
        if separate:assert left[1]>200 and left[0]<50 and right[0]>200 and right[1]>200
        else:assert left[0]>200 and left[2]<50 and right[2]>200 and right[0]<50
    audio=subprocess.run(['ffmpeg','-v','error','-i',str(output),'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','pipe:1'],capture_output=True,check=True).stdout
    samples=array.array('h',audio);frequency=sum((a<0)!=(b<0) for a,b in zip(samples,samples[1:]))/2/(len(samples)/8000)
    assert abs(frequency-(880 if separate else 440))<25
    if separate:
        samples=samples[800:-800]
        def amplitude(f):
            return math.hypot(sum(v*math.sin(2*math.pi*f*i/8000) for i,v in enumerate(samples)),sum(v*math.cos(2*math.pi*f*i/8000) for i,v in enumerate(samples)))
        assert amplitude(440)<amplitude(880)*.03
    # Gameplay geometry and split don't affect a webcam-only result.
    changed=post('/projects/'+p['id']+'/cuts',{**cut,'game':dict(x=.4,y=.4,w=.5,h=.5),'split':.7,'baseVolume':0})
    reused=post('/projects/'+p['id']+'/export',{'ids':[changed['id']],'requestId':'same-camera-only-1234567'})
    assert reused['created']==0 and reused['ids']==[jid]
    # Switching the camera mirror does change the final video.
    changed=post('/projects/'+p['id']+'/cuts',{**changed,'camFlip':not mirror})
    assert post('/projects/'+p['id']+'/export',{'ids':[changed['id']],'requestId':'camera-flipped-1234567'})['created']==1


@pytest.mark.parametrize('muted',[False,True])
def test_webcam_reaction_never_falls_back_to_base_audio(tmp_path,muted):
    base=tmp_path/'base.mp4';reaction=tmp_path/'reaction.mp4';silent=tmp_path/'silent.mp4'
    source(base,'red','blue',440);source(reaction,'lime','yellow',880)
    subprocess.run(['ffmpeg','-v','error','-i',str(reaction),'-c:v','copy','-an','-y',str(silent)],check=True)
    p=post('/projects',{'name':'Só minha opinião'})
    for path,role in [(base,'base'),(reaction if muted else silent,'reaction')]:
        response=client.post('/api/projects/'+p['id']+'/media?role='+role,content=path.read_bytes(),headers={**HEAD,'X-Video-Extension':'.mp4'})
        assert response.status_code==200,response.text
        if role=='reaction': rid=response.json()['id']
    cut=post('/projects/'+p['id']+'/cuts',dict(start=0,end=.6,layout='webcam',reactionId=rid,reactionOffset=0,baseVolume=1,reactionVolume=0 if muted else 1,cam=dict(x=0,y=0,w=1,h=1)))
    jid=completed_result(p,cut,'silent-camera-123456789')
    assert probe(DATA/p['id']/(jid+'.mp4'))['audio'] is False
