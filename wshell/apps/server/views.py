#coding=utf-8
import os, sys
import locale
from uliweb import expose
from uliweb.utils.common import log, import_attr, get_uuid
from uliweb.utils.date import now
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
import shlex
from gevent import subprocess as sub, spawn, monkey, sleep
from subprocess import CalledProcessError

monkey.patch_all(subprocess=True)

encoding = locale.getdefaultlocale()[1] or 'utf8'
platform = sys.platform
download_tokens = {}

def can_download(filename):
    import errno
    
    fp = None
    try:
        fp = open(filename)
        return True
    except IOError as e:
        if e.errno == errno.EACCES:
            return False
        # Not a permission error.
        raise
    finally:
        if fp:
            fp.close()
        
@expose('/')
def index():
    return {}

@expose('/download')
def download():
    from uliweb.utils.filedown import filedown
    
    token = request.GET.get('token')
    filename = download_tokens.pop(token, None)
    if filename:
        return filedown(request.environ, filename, action='download', 
            real_filename=filename)
        
    return 'Error: token is not right'

@expose('/upload')
def upload():
    _id = request.GET.get('id')
    path = request.POST.get('path')
    
    if 'file' in request.files:
        fname = functions.save_file(os.path.join(path, request.files['file'].filename), request.files['file'].stream, convert=False)
        return json({'success':True, 'filename':fname})
    else:
        return json({'success':False, 'message':form.error['file']})

class Command(object):
    cwd = ''
    def __init__(self, cmd_args, command, server):
        
        if platform == 'win32':
            cmds = ['cmd', '/c']
        else:
            cmds = []
        
        self.server = server
        self._cmd_args = cmd_args
        self.cmd_args = cmds + cmd_args
        self.command = command
        self.id = command['id']
        self.timestamp = now()
        self.old_cwd = command['cwd']
        self.cwd = self.cwd or self.old_cwd
        self.process = None
        self.status = -1
        
        self.init()
        self.create_process()
        self.create_output()
        
    def init(self):
        pass
    
    def create_process(self):
        self.status = 0 #starting
        self.process = sub.Popen(self.cmd_args, stdin=sub.PIPE, stdout=sub.PIPE, 
            stderr=sub.STDOUT, shell=False, cwd=self.old_cwd)
            
    def create_output(self):
        def output():
            while self.process.poll() is None:
                line = self.process.stdout.readline()
                self.process.timestamp = now()
                if line:
                    self.output('return', self.server.safe_encode(line.rstrip()))
            self.output('cwd', self.server.safe_encode(self.old_cwd))
            self.status = 1 #finished
                
        spawn(output)
     
    def output(self, event, message, output=None):
        if output:
            output['id'] = self.command['id']
            self.server.emit(event, output)
        else:
            self.server.emit(event, {'output':message, 'id':self.command['id']})
        
class MysqlCommand(Command):
    cwd = 'mysql'
    
    def init(self):
        if '-n' not in self.cmd_args or '--unbuffered' not in self.cmd_args:
            self.cmd_args.append('-n')
        if '-t' not in self.cmd_args or '--table' not in self.cmd_args:
            self.cmd_args.append('-t')
        self.cmd_args.append('--default-character-set=utf8')
           
class DownloadCommand(Command):
    """
    command: download filename
    """
    def create_process(self):
        return
    
    def create_output(self):
        def p():
            if len(self._cmd_args) > 1:
                filename = os.path.join(self.command['cwd'], self._cmd_args[1])
                if not os.path.exists(filename):
                    self.output('err', 'filename %s is not existed!' % filename)
                    return
                try:
                    flag = can_download(filename)
                    if not flag:
                        self.output('err', 'filename %s is not existed!' % filename)
                        return
                except Exception as e:
                    self.output('err', str(e))
                    return
                
                token = get_uuid()
                #todo check the right of the file
                url = '/download?token=' + token
                download_tokens[token] = filename
                self.output('download', url)
            else:
                self.output('err', 'You should give filename paramter')
        p()
        self.status = 1
       
class ShellNamespace(BaseNamespace):

    def initialize(self):
        self.shells = {}
        self.log("Socketio session started")
        self.check_processes()

    def check_processes(self):
        from uliweb import settings
        
        def check():
            while 1:
                #self.log('checking...')
                r = []
                for k, p in self.shells.items():
                    if p.status == 1:
                        #finished should be remove
                        r.append(k)
                    elif p.status == 0:
                        t = now()
                        if (t - p.timestamp).seconds > settings.WSHELL.stop_interval:
                            p.output('err', 'Time is up, so the process will be killed!')
                            self.log('Time is up, killing process %r' % p.process)
                            self.close_process(p)
                        
                for k in r:
                    del self.shells[k]
                sleep(0.5)
        spawn(check)
                        
    def log(self, message):
        log.info("[{0}] {1}".format(self.socket.sessid, message))

    def safe_encode(self, text):
        if isinstance(text, unicode):
            return text.encode('utf8')
        try:
            unicode(text, 'utf8')
            return text
        except UnicodeDecodeError:
            t = unicode(text, encoding).encode('utf8')
            return t
        
    def do(self, command):
        from uliweb import settings
        
        cmd = command['cmd']
        _id = command['id']
        last_process = self.shells.get(_id)
        if last_process and last_process.process and last_process.process.poll() is None:
            process = last_process.process
            process.stdin.write(cmd + '\n')
            process.stdin.flush()
        else:
            cmd_args = shlex.split(cmd)
            cmd_path = settings.COMMANDS.get(cmd_args[0])
            if cmd_path:
                cmd_cls = import_attr(cmd_path)
            else:
                cmd_cls = Command
            
            p = cmd_cls(cmd_args, command, self)
            self.shells[_id] = p
            #p.process may be None, so that it can do other thing more than commad line
            if p.process and p.process.poll() is None:
                p.output('cwd', self.safe_encode(p.cwd))
            
    def close_process(self, p):
        if p.process and p.process.poll() is None:
            log.debug('kill process ' + str(p.process.pid))
            if platform == 'win32':
                sub.call(['taskkill', '/F', '/T', '/PID', str(p.process.pid)])
            else:
                p.process.kill()
        p.status = 1
        
    def reset_all(self, id):
        for p in self.shells.values():
            self.close_process(p)
        self.shells = {}
                
    def on_login(self, data):
        from uliweb.utils.common import get_uuid
        from uliweb import settings, application
        
        if data['user'] == settings.WSHELL.user and data['password'] == settings.WSHELL.password:
            token = get_uuid()
        else:
            token = False
        
        os.environ['PROJECT'] = application.project_dir
        path = os.path.expandvars(settings.WSHELL.login_path)
        self.emit('logined', {'output':path, 'token':token, 'id':data['id']})
    
    def on_cmd(self, command):
        cmd = command['cmd']

        self.log('cmd : ' + cmd + ' id=' + command['id'])
        if not cmd:
            return
        
        if cmd.startswith('cd '):
            if platform == 'win32':
                cmd = '%s && cd' % cmd
            else:
                cmd = '%s && pwd' % cmd
            try:
                result = sub.check_output(cmd, stderr=sub.STDOUT, shell=True, cwd=command['cwd'])
                cwd = result.rstrip()
                if cwd:
                    self.emit('cwd', {'output':self.safe_encode(cwd), 'id':command['id']})
            except CalledProcessError as e:
                result = e.output
                self.emit('return', {'output':self.safe_encode(result), 'id':command['id']})
        elif cmd == 'reset':
            self.reset_all(command['id'])
        else:
            self.do(command)

    def recv_disconnect(self):
        # Remove nickname from the list.
        self.log('Disconnected')
        self.disconnect(silent=True)
        return True

@expose('/socket.io/<path:path>')
def socketio(path):
    try:
        socketio_manage(request.environ, {'/shell': ShellNamespace}, request)
    except:
        log.exception("Exception while handling socketio connection")
    return response
    
