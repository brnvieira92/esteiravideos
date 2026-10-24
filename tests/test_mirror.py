import subprocess
import pytest
from tests.test_workflow import client, HEAD, post, completed_result
from backend.core import DATA, validate_cut


@pytest.mark.parametrize('separate',[False,True])
def test_mirror_changes_only_camera_pixels_and_preserves_original(tmp_path,separate):
    path=tmp_path/'sides.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=320x180:r=24:d=1,drawbox=x=160:y=0:w=160:h=180:color=blue:t=fill','-c:v','libx264','-threads','1','-y',str(path)],check=True)
    p=post('/projects',{'name':'Espelho'})
    def upload(role):
        r=client.post('/api/projects/'+p['id']+'/media?role='+role,content=path.read_bytes(),headers={**HEAD,'X-Video-Extension':'.mp4'})
        assert r.status_code==200,r.text
        return r.json()
    base=upload('base'); reaction=upload('reaction') if separate else None
    outputs=[]
    for mirror in [False,True]:
        d=dict(name='Espelho',start=0,end=.6,layout='combined',split=.5,game=dict(x=0,y=0,w=1,h=1),cam=dict(x=0,y=0,w=1,h=1),camFlip=mirror)
        if reaction: d.update(reactionId=reaction['id'],reactionOffset=0)
        saved=post('/projects/'+p['id']+'/cuts',d)
        assert saved['camFlip']==mirror
        assert next(c for c in client.get('/api/projects/'+p['id']).json()['cuts'] if c['id']==saved['id'])['camFlip']==mirror
        jid=completed_result(p,saved,'mirror-'+str(mirror)+'-123456789')
        output=DATA/p['id']/(jid+'.mp4')
        pixels=subprocess.run(['ffmpeg','-v','error','-i',str(output),'-vf','format=rgb24','-frames:v','1','-f','rawvideo','pipe:1'],capture_output=True,check=True).stdout
        outputs.append([tuple(pixels[i:i+3]) for i in [(y*1080+x)*3 for x,y in [(270,480),(810,480),(270,1440),(810,1440)]]])
    plain,flipped=outputs
    red=lambda p:p[0]>200 and p[2]<50
    blue=lambda p:p[2]>200 and p[0]<50
    assert red(plain[0]) and blue(plain[1])
    assert blue(flipped[0]) and red(flipped[1])
    assert red(flipped[2]) and blue(flipped[3])  # Gameplay stays in its original orientation.
    assert client.get('/api/media/'+base['id']).content==path.read_bytes()
    if reaction: assert client.get('/api/media/'+reaction['id']).content==path.read_bytes()


def test_mirror_default_and_validation():
    assert validate_cut(dict(start=0,end=1),2)['camFlip'] is False
    with pytest.raises(ValueError): validate_cut(dict(start=0,end=1,camFlip='false'),2)
