"""Small standard-library CDP driver; ordinary browser security is retained."""
import base64,hashlib,json,os,shutil,signal,socket,struct,subprocess,tempfile,time
from pathlib import Path
import urllib.parse,urllib.request

class WebSocket:
    """Minimal RFC6455 client: masked writes, fragmentation, ping/pong."""
    def __init__(self,url):
        u=urllib.parse.urlparse(url)
        assert u.scheme=='ws' and u.hostname in ('localhost','127.0.0.1')
        self.sock=socket.create_connection((u.hostname,u.port),timeout=30)
        self.buf=b''
        key=base64.b64encode(os.urandom(16)).decode()
        request=(f'GET {u.path}{"?"+u.query if u.query else ""} HTTP/1.1\r\n'
                 f'Host: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                 f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
        self.sock.sendall(request.encode())
        while b'\r\n\r\n' not in self.buf:self.buf+=self.sock.recv(65536)
        headers,self.buf=self.buf.split(b'\r\n\r\n',1)
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if b' 101 ' not in headers or expected not in headers:raise RuntimeError(headers.decode())
    def read(self,n):
        while len(self.buf)<n:
            block=self.sock.recv(max(65536,n-len(self.buf)))
            if not block:raise EOFError('Chrome WebSocket closed')
            self.buf+=block
        out,self.buf=self.buf[:n],self.buf[n:]
        return out
    def send(self,data,opcode=1):
        data=data.encode() if isinstance(data,str) else data
        n=len(data);mask=os.urandom(4);head=bytes([0x80|opcode])
        head+=bytes([0x80|n]) if n<126 else bytes([0x80|126])+struct.pack('!H',n) if n<65536 else bytes([0x80|127])+struct.pack('!Q',n)
        self.sock.sendall(head+mask+bytes(v^mask[i%4] for i,v in enumerate(data)))
    def recv(self):
        chunks=[]
        while True:
            a,b=self.read(2);n=b&127
            if n==126:n=struct.unpack('!H',self.read(2))[0]
            elif n==127:n=struct.unpack('!Q',self.read(8))[0]
            mask=self.read(4) if b&128 else None
            payload=self.read(n)
            if mask:payload=bytes(v^mask[i%4] for i,v in enumerate(payload))
            op=a&15
            if op==8:raise EOFError('Chrome sent WebSocket close')
            if op==9:self.send(payload,10);continue
            if op==10:continue
            if op not in (0,1):raise RuntimeError('Unsupported WebSocket opcode '+str(op))
            chunks.append(payload)
            if a&128:return b''.join(chunks).decode()
    def close(self):
        try:self.sock.close()
        except OSError:pass

class ChromeSession:
    def __init__(self,url=None,width=1920,height=1080,timeout=45,headless=True):
        self.width=width;self.height=height;self.timeout=timeout;self.events=[];self.counter=0
        self.profile=Path(tempfile.mkdtemp(prefix='suvlab-browser-test-'))
        self.log=(self.profile/'chrome.log').open('wb');self.ws=None
        self.process=subprocess.Popen([os.environ.get('CHROME_BIN','google-chrome')]+(['--headless=new'] if headless else [])+['--disable-gpu','--no-sandbox',
            '--disable-background-networking','--disable-component-update',
            '--disable-default-apps','--disable-extensions','--no-first-run','--no-default-browser-check',
            '--hide-scrollbars','--force-device-scale-factor=1','--remote-debugging-address=127.0.0.1',
            '--remote-debugging-port=0',f'--user-data-dir={self.profile}',f'--window-size={width},{height}',
            'about:blank'],stdout=self.log,stderr=self.log,start_new_session=True)
        deadline=time.monotonic()+timeout
        portfile=self.profile/'DevToolsActivePort'
        while not portfile.exists():
            if self.process.poll() is not None:raise RuntimeError((self.profile/'chrome.log').read_text())
            if time.monotonic()>deadline:raise TimeoutError('Chrome CDP startup')
            time.sleep(.05)
        self.port=int(portfile.read_text().splitlines()[0])
        with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/list',timeout=5) as response:pages=json.load(response)
        page=next(x for x in pages if x['type']=='page')
        self.ws=WebSocket(page['webSocketDebuggerUrl'])
        for method in ('Page.enable','Runtime.enable','Log.enable','Network.enable'):self.call(method)
        self.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
        self.call('Page.bringToFront')
        if url:self.navigate(url)
    def call(self,method,params=None):
        self.counter+=1;ident=self.counter
        self.ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            self.ws.sock.settimeout(max(.01,deadline-time.monotonic()))
            message=json.loads(self.ws.recv())
            if message.get('id')==ident:
                if 'error' in message:raise RuntimeError(f'{method}: {message["error"]}')
                return message.get('result',{})
            self.events.append(message)
        raise TimeoutError(method)
    def evaluate(self,expression,await_promise=True):
        r=self.call('Runtime.evaluate',{'expression':expression,'awaitPromise':await_promise,'returnByValue':True,'userGesture':True})
        if 'exceptionDetails' in r:raise RuntimeError(json.dumps(r['exceptionDetails']))
        return r.get('result',{}).get('value')
    def navigate(self,url):
        self.call('Page.navigate',{'url':str(url)})
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            if self.evaluate('document.readyState === "complete"'):return
            time.sleep(.05)
        raise TimeoutError('Page load did not finish')
    def screenshot(self,path=None):
        r=self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False,'fromSurface':True,
            'clip':{'x':0,'y':0,'width':self.width,'height':self.height,'scale':1}})
        data=base64.b64decode(r['data'])
        if path:
            path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return data
    def key(self,key):
        code={'ArrowRight':39,'ArrowLeft':37,'ArrowUp':38,'ArrowDown':40,'PageUp':33,'PageDown':34,'Home':36,'End':35,'Escape':27,'Enter':13,' ':32}.get(key,ord(key.upper()[0]))
        args={'key':key,'windowsVirtualKeyCode':code,'nativeVirtualKeyCode':code}
        text='\r' if key=='Enter' else key if len(key)==1 else ''
        self.call('Input.dispatchKeyEvent',{'type':'keyDown',**args,**({'text':text,'unmodifiedText':text} if text else {})})
        self.call('Input.dispatchKeyEvent',{'type':'keyUp',**args})
    def close(self):
        if self.ws:self.ws.close()
        if self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGTERM)
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
        self.log.close();shutil.rmtree(self.profile,ignore_errors=True)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
