import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from tests.test_workflow import client, HEAD, post, setup_project, completed_result
from backend.app import app
from backend.core import db,DATA


def automatic(pid,**extra):
    return post('/projects/'+pid+'/cuts',dict(start=.1,end=.8,autoName=True,name='sugestão desatualizada',**extra))


def test_numbering_survives_rename_deletion_and_stale_clients():
    p,_,first=setup_project()
    second=automatic(p['id']);assert second['name']==p['name']+' — parte 2'
    renamed=post('/projects/'+p['id']+'/cuts',{**second,'name':'Meu título'})
    assert renamed['name']=='Meu título'
    assert client.delete('/api/cuts/'+first['id'],headers=HEAD).status_code==200
    assert client.delete('/api/cuts/'+second['id'],headers=HEAD).status_code==200
    third=automatic(p['id']);assert third['name']==p['name']+' — parte 3'
    post_name=client.patch('/api/projects/'+p['id'],json={'name':'Nome novo'},headers=HEAD)
    assert post_name.status_code==200
    assert automatic(p['id'])['name']=='Nome novo — parte 4'
    duplicate=client.post('/api/projects/'+p['id']+'/cuts',json={**third,'id':None},headers=HEAD)
    assert duplicate.status_code==422
    assert client.get('/api/projects/'+p['id']).json()['nextCutName']=='Nome novo — parte 5'


def test_concurrent_names_and_exports_are_allocated_atomically():
    p,_,_=setup_project()
    def create(_):
        with TestClient(app) as other:
            r=other.post('/api/projects/'+p['id']+'/cuts',json={'start':0,'end':1,'autoName':True},headers=HEAD)
            assert r.status_code==200,r.text
            return r.json()
    with ThreadPoolExecutor(max_workers=2) as pool: cuts=list(pool.map(create,range(2)))
    assert {c['name'] for c in cuts}=={p['name']+' — parte 2',p['name']+' — parte 3'}
    def export(i):
        with TestClient(app) as other:
            r=other.post('/api/projects/'+p['id']+'/export',json={'ids':[cuts[i]['id']],'requestId':'concurrent-export-'+str(i)},headers=HEAD)
            assert r.status_code==200,r.text
            return r.json()
    with ThreadPoolExecutor(max_workers=2) as pool: replies=list(pool.map(export,range(2)))
    assert replies[0]['ids']==replies[1]['ids']
    assert sum(r['created'] for r in replies)==1
    assert sum(len(r['skipped']) for r in replies)==1


def test_completed_exports_are_reused_but_render_changes_and_deletion_allow_new_output():
    p,_,cut=setup_project();jid=completed_result(p,cut,'initial-render-1234567')
    response=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'fresh-request-12345678'})
    assert response['ids']==[jid] and response['created']==0 and response['skipped'][0]['state']=='concluído'
    renamed=post('/projects/'+p['id']+'/cuts',{**cut,'name':'Outro nome'})
    assert post('/projects/'+p['id']+'/export',{'ids':[renamed['id']],'requestId':'rename-only-123456789'})['ids']==[jid]
    changed=post('/projects/'+p['id']+'/cuts',{**renamed,'camFlip':True})
    new=post('/projects/'+p['id']+'/export',{'ids':[changed['id']],'requestId':'changed-render-1234567'})
    assert new['created']==1 and new['ids']!=[jid]
    post('/jobs/'+new['ids'][0]+'/cancel',{})
    # History survives deletion; explicit regeneration remains available.
    assert client.delete('/api/jobs/'+jid,headers=HEAD).status_code==200
    post('/projects/'+p['id']+'/cuts',renamed)
    skipped=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'skip-deleted-12345678'})
    assert skipped['created']==0 and skipped['skipped'][0]['state']=='excluído'
    again=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'after-delete-12345678','force':True})
    assert again['created']==1 and again['ids']!=[jid]


def test_preview_is_separate_and_legacy_completed_jobs_are_recognized():
    p,_,cut=setup_project();jid=completed_result(p,cut,'legacy-render-1234567')
    with db() as c:
        d=json.loads(c.execute('SELECT snapshot FROM jobs WHERE id=?',(jid,)).fetchone()[0]);d.pop('kind');d.pop('sourceCutId')
        c.execute('UPDATE jobs SET snapshot=? WHERE id=?',(json.dumps(d),jid))
    assert post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'legacy-match-12345678'})['ids']==[jid]
    preview=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'preview':True,'requestId':'preview-new-12345678'})
    assert preview['created']==1 and preview['ids']!=[jid]
    assert post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'full-after-preview-1234'})['ids']==[jid]
    # A missing output is still remembered; explicit regeneration is available.
    (DATA/p['id']/(jid+'.mp4')).unlink()
    assert post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'missing-output-1234567'})['created']==0
    assert post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'force-missing-1234567','force':True})['created']==1


def test_legacy_duplicate_titles_remain_editable_and_failed_exports_can_retry():
    p,_,cut=setup_project()
    legacy={k:v for k,v in cut.items() if k!='id'}
    with db() as c: c.execute('INSERT INTO cuts VALUES (?,?,?)',('legacy-copy-'+p['id'],p['id'],json.dumps(legacy)))
    changed=post('/projects/'+p['id']+'/cuts',{**cut,'camFlip':True})
    assert changed['name']==cut['name']
    first=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'will-cancel-123456789'})
    post('/jobs/'+first['ids'][0]+'/cancel',{})
    second=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'after-cancel-123456789'})
    assert second['created']==1
    retry=post('/jobs/'+first['ids'][0]+'/retry',{})
    assert retry['reused'] and retry['id']==second['ids'][0]
    forced=post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'force-active-123456789','force':True})
    assert forced['created']==0 and forced['ids']==second['ids']
    with db() as c: c.execute("UPDATE jobs SET state='falhou' WHERE id=?",(second['ids'][0],))
    assert post('/projects/'+p['id']+'/export',{'ids':[cut['id']],'requestId':'after-failure-123456789'})['created']==1
