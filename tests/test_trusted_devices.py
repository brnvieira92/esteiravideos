import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from tests.test_workflow import HEAD
import backend.app as module
from backend.core import db
from backend.trusted_devices import COOKIE,LIFETIME


@pytest.fixture
def pairing(monkeypatch):
    monkeypatch.setattr(module,'LAN',True)
    monkeypatch.setattr(module,'sessions',{})
    monkeypatch.setattr(module,'attempts',{})
    monkeypatch.setattr(module,'pairing_expiry',time.time()+600)
    with db() as c: c.execute('DELETE FROM trusted_devices')
    yield
    with db() as c: c.execute('DELETE FROM trusted_devices')


def phone(https=True):
    return TestClient(module.app,base_url=('https' if https else 'http')+'://192.168.1.10',client=('192.168.1.40',50000))


def pair(client,remember=True):
    return client.post('/api/pair',json={'code':module.pairing,'remember':remember,'deviceName':'Meu celular'},headers=HEAD)


def test_https_trust_survives_session_reset_and_stores_only_a_hash(pairing,monkeypatch):
    with phone() as p:
        r=pair(p);assert r.status_code==200,r.text
        token=p.cookies[COOKIE]
        cookie=next(v for v in r.headers.get_list('set-cookie') if v.startswith(COOKIE+'=') and 'Max-Age=0' not in v)
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/' in cookie
        assert f'Max-Age={LIFETIME}' in cookie
        assert not module.sessions
        with db() as c: row=dict(c.execute('SELECT * FROM trusted_devices').fetchone())
        assert row['token_hash']==hashlib.sha256(token.encode()).hexdigest()
        assert token not in str(row)
        module.sessions.clear();monkeypatch.setattr(module,'pairing','NEWCODE')
        assert p.get('/api/projects').status_code==200
        info=p.get('/api/session');assert info.json()['paired'] and info.json()['trusted']
        assert info.json()['deviceName']=='Meu celular' and not info.json()['canManageDevices']
        assert info.headers['cache-control']=='no-store'
        # HTTPS trust is never accepted over HTTP, even with a manually replayed cookie.
        with phone(False) as plain: assert plain.get('/api/projects',headers={'Cookie':COOKIE+'='+token}).status_code==401
        assert p.get('/api/projects',headers={'Cookie':COOKIE+'='+token[:-1]+'!'}).status_code==401
        with db() as c: c.execute('UPDATE trusted_devices SET expires=?',(time.time()-1,))
        assert p.get('/api/projects').status_code==401 and not p.get('/api/session').json()['paired']


def test_temporary_pairing_and_http_remember_refusal(pairing):
    with phone(False) as p:
        assert pair(p).status_code==422
        with db() as c: assert c.execute('SELECT count(*) FROM trusted_devices').fetchone()[0]==0
        assert pair(p,False).status_code==200
        assert p.get('/api/projects').status_code==200
        module.sessions.clear()
        assert p.get('/api/projects').status_code==401


def test_remote_cannot_manage_trust_and_local_revocation_blocks_next_request(pairing,monkeypatch):
    with phone() as p:
        assert pair(p).status_code==200
        token=p.cookies[COOKIE]
        assert p.get('/api/devices').status_code==403
        assert p.delete('/api/devices',headers={**HEAD,'X-Forwarded-For':'127.0.0.1','Host':'localhost'}).status_code==403
        # The normal desktop launcher allows management only from an actual loopback client.
        monkeypatch.setattr(module,'LAN',False)
        with TestClient(module.app,base_url='http://localhost',client=('127.0.0.1',40000)) as pc:
            devices=pc.get('/api/devices').json()
            assert len(devices)==1 and devices[0]['name']=='Meu celular'
            assert 'token_hash' not in devices[0] and token not in str(devices)
            assert pc.get('/api/devices',headers={'Host':'attacker.example'}).status_code==403
            assert pc.delete('/api/devices/'+devices[0]['id'],headers=HEAD).status_code==200
        monkeypatch.setattr(module,'LAN',True)
        assert p.get('/api/projects').status_code==401


def test_self_forgetting_and_revoking_all_are_persistent(pairing,monkeypatch):
    with phone() as p:
        assert pair(p).status_code==200
        token=p.cookies[COOKIE]
        assert p.post('/api/unpair',headers=HEAD).status_code==200
        assert p.get('/api/projects',headers={'Cookie':COOKIE+'='+token}).status_code==401
        assert pair(p).status_code==200
        monkeypatch.setattr(module,'LAN',False)
        with TestClient(module.app,base_url='http://localhost',client=('127.0.0.1',40000)) as pc:
            assert pc.delete('/api/devices',headers=HEAD).status_code==200
        monkeypatch.setattr(module,'LAN',True)
        assert p.get('/api/projects').status_code==401
