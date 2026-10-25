"""Revocable, HTTPS-only remembered pairing. Only SHA-256 token hashes persist."""
import hashlib
import ipaddress
import re
import secrets
import time
from fastapi import HTTPException
from .core import db,uid

COOKIE='__Host-esteira_trusted'
LIFETIME=90*86400


def local_admin(request):
    try: local=ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError,AttributeError): return False
    return local and request.url.hostname in ('127.0.0.1','localhost','::1')


def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()


def current(request):
    if request.url.scheme!='https': return None
    token=request.cookies.get(COOKIE,'')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token): return None
    now=time.time()
    with db() as c:
        row=c.execute('SELECT * FROM trusted_devices WHERE token_hash=? AND expires>?',(token_hash(token),now)).fetchone()
        if not row: return None
        if row['last_used']<now-3600: c.execute('UPDATE trusted_devices SET last_used=? WHERE id=?',(now,row['id']))
    return dict(row)


def remember(request,response,label):
    if request.url.scheme!='https': raise HTTPException(422,'Para confiar neste dispositivo, use o endereço HTTPS do aplicativo.')
    token=secrets.token_urlsafe(32); now=time.time();expires=now+LIFETIME
    ua=request.headers.get('user-agent','')
    default='iPhone / iPad' if any(x in ua for x in ('iPhone','iPad')) else 'Android' if 'Android' in ua else 'Navegador'
    name=' '.join(str(label or default).split())[:80] or default
    with db() as c:
        c.execute('DELETE FROM trusted_devices WHERE expires<=?',(now,))
        c.execute('INSERT INTO trusted_devices VALUES (?,?,?,?,?,?)',(uid(),token_hash(token),name,now,now,expires))
    response.set_cookie(COOKIE,token,max_age=LIFETIME,httponly=True,secure=True,samesite='strict',path='/')


def forget(request,response):
    token=request.cookies.get(COOKIE,'')
    if token and request.url.scheme=='https':
        with db() as c: c.execute('DELETE FROM trusted_devices WHERE token_hash=?',(token_hash(token),))
    response.delete_cookie(COOKIE,secure=True,httponly=True,samesite='strict',path='/')
