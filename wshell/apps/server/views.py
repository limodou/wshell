#coding=utf-8
import os, sys
import locale
from uliweb import expose
from uliweb.utils.common import log, import_attr
from uliweb.utils.date import now
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
import shlex
from gevent import subprocess as sub, spawn, monkey
from subprocess import CalledProcessError

monkey.patch_all(subprocess=True)

encoding = locale.getdefaultlocale()[1] or 'utf8'
platform = sys.platform

@expose('/')
def index():
    return {'outputLimit':settings.WSHELL.outputLimit}

class Command(object):
    cwd = ''
    def __init__(self, cmd_args, command, server):
        
        if platform == 'win32':
            cmds = ['cmd', '/c']
        else:
            cmds = ['/bin/bash', '-c']
        
        self.server = server
        self.cmd_args = cmds + cmd_args
        self.command = command
        self.id = command['id']
        self.timestamp = now()
        self.old_cwd = command['cwd']
        self.cwd = self.cwd or self.old_cwd
        
        self.init()
        self.create_process()
        self.create_output()
        
    def init(self):
        pass
    
    def create_process(self):
        self.process = sub.Popen(self.cmd_args, stdin=sub.PIPE, stdout=sub.PIPE, 
            stderr=sub.STDOUT, 
            shell=False,
            cwd=self.old_cwd)
            
    def create_output(self):
        def output():
            while self.process.poll() is None:
                line = self.process.stdout.readline().rstrip()
                self.server.emit('return', {'output':self.server.safe_encode(line), 'id':self.id})
            self.server.emit('cwd', {'output':self.server.safe_encode(self.old_cwd), 'id':self.id})
                
        spawn(output)
     
class MysqlCommand(Command):
    cwd = 'mysql'
    
    def init(self):
        if '-n' not in self.cmd_args or '--unbuffered' not in self.cmd_args:
            self.cmd_args.append('-n')
        if '-t' not in self.cmd_args or '--table' not in self.cmd_args:
            self.cmd_args.append('-t')
        self.cmd_args.append('--default-character-set=utf8')
            
class ShellNamespace(BaseNamespace):

    def initialize(self):
#        self.logger = app.logger
        self.shells = {}
        self.log("Socketio session started")

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
        if last_process and last_process.process.poll() is None:
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
            if p.process.poll() is None:
                self.emit('cwd', {'output':self.safe_encode(p.cwd), 'id':p.id})
            
    def close_process(self, process):
        if process.poll() is None:
            log.debug('kill process ' + str(process.pid))
            if platform == 'win32':
                sub.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.kill()
        
    def reset_all(self, id):
        for p in self.shells.values():
            self.close_process(p.process)
        self.shells = {}
        self.emit('return', {'output':'', 'id':id})
                
    def on_login(self, data):
        from uliweb.utils.common import get_uuid
        from uliweb import settings
        
        if data['user'] == settings.WSHELL.user and data['password'] == settings.WSHELL.password:
            token = get_uuid()
        else:
            token = False
        
        self.emit('logined', {'output':os.getcwd(), 'token':token, 'id':data['id']})
    
    def on_cmd(self, command):
        cmd = command['cmd']

        self.log('cmd : ' + cmd + ' id=' + command['id'])
        if not cmd:
            self.emit('return', {'output':'', 'id':command['id']})
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
    
