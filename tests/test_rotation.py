import json
import subprocess
import pytest
from tests.test_workflow import client, HEAD, post, sample
from backend.core import DATA, db, probe
from backend.worker import run_job


@pytest.mark.parametrize('angle',[90,270,180,0])
def test_phone_rotation_and_legacy_metadata(tmp_path,angle):
    original=tmp_path/'original.mp4'; rotated=tmp_path/'phone.mp4'
    sample(original)
    subprocess.run(['ffmpeg','-v','error','-display_rotation',str(angle),'-i',str(original),'-c','copy','-y',str(rotated)],check=True)
    expected=(180,320) if angle in (90,270) else (320,180)
    meta=probe(rotated)
    assert (meta['width'],meta['height'])==expected
    p=post('/projects',{'name':'Telefone girado'})
    def upload(role):
        r=client.post('/api/projects/'+p['id']+'/media?role='+role,content=rotated.read_bytes(),headers={**HEAD,'X-Video-Extension':'.mp4'})
        assert r.status_code==200,r.text
        return r.json()
    base=upload('base'); reaction=upload('reaction')
    assert (reaction['width'],reaction['height'])==expected
    # Simulate saved media from 0.4.1: raw encoded dimensions, no orientation marker.
    stale={**meta,'width':320,'height':180};stale.pop('orientationVersion');stale.pop('rotation')
    with db() as c: c.execute('UPDATE media SET meta=? WHERE project_id=?',(json.dumps(stale),p['id']))
    # Export without opening the project first must refresh the metadata too.
    cut=post('/projects/'+p['id']+'/cuts',dict(name='React vertical',start=.1,end=.7,layout='combined',reactionId=reaction['id'],reactionOffset=0,game=dict(x=0,y=0,w=1,h=1),cam=dict(x=0,y=0,w=1,h=1)))
    jid=post('/projects/'+p['id']+'/export',dict(ids=[cut['id']],requestId='rotation-legacy-123456'))['ids'][0]
    with db() as c:
        job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    snapshot=json.loads(job['snapshot'])
    assert (snapshot['meta']['width'],snapshot['meta']['height'])==expected
    assert (snapshot['reactionMeta']['width'],snapshot['reactionMeta']['height'])==expected
    # Simulate a failed/queued job from the old version; worker fixes it on retry.
    snapshot['meta']=stale;snapshot['reactionMeta']=stale;job['snapshot']=json.dumps(snapshot)
    run_job(job)
    with db() as c: result=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    assert result['state']=='concluído',result
    assert (probe(result['output'])['width'],probe(result['output'])['height'])==(1080,1920)
    updated=client.get('/api/projects/'+p['id']).json()
    assert (updated['media']['width'],updated['media']['height'])==expected
    assert (updated['reactions'][0]['width'],updated['reactions'][0]['height'])==expected
    with db() as c: assert all(json.loads(r[0])['orientationVersion']==1 for r in c.execute('SELECT meta FROM media WHERE project_id=?',(p['id'],)))
    assert client.get('/api/media/'+base['id']).content==rotated.read_bytes()
