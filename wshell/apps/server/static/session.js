/******************************************************
 * Author: limodou@gmail
 ******************************************************/

version = '1.0'

function S4(){   
   return (((1+Math.random())*0x10000)|0).toString(16).substring(1);   
}    
function getId(){   
   return S4()+S4();   
}

WEB_SOCKET_SWF_LOCATION = "/static/WebSocketMain.swf";
WEB_SOCKET_DEBUG = true;

var socket = io.connect('/shell');

function select_term(id){
    var term = get_term(id);
    term.focus(true);
    term.scroll(1000);
}

function get_term(id){
    var _id = id || model.cur;
    for(var i=0; i<model.shells.length; i++){
        var x = model.shells[i];
        if (x.id == _id){
            return $('#'+x.id).terminal();
        }
    }
}

function get_item(id){
    var _id = id || model.cur;
    for(var i=0; i<model.shells.length; i++){
        var x = model.shells[i];
        if (x.id == _id){
            return x;
        }
    }
}


socket.on('return', function(data){
    var term = get_term(data.id);
    term.echo(data.output);
//    term.resume();
});
socket.on('cwd', function(data){
    var term = get_term(data.id);
    term.set_prompt(data.output + '> ');
    var item = get_item(data.id);
    item.cwd = data.output;
//    term.resume();
});

avalon.config({
   interpolate: ["{%", "%}"]
});

var _id = getId();
var model = avalon.define("shell", function(vm){
    vm.shells = [{title:_id, id:_id, url:'/shell?id=' + _id, socket:null}];
    vm.cur = _id;
    vm.newSession = function(){
        var _id = getId();
        var title = _id;
        vm.shells.push({title:title, url:'/shell?id=' + _id, id:_id});
        setTimeout(function(){
            init_terminal(model.shells[model.shells.length-1]);
            select_term();
        }, 500);
        vm.cur = _id;
    }
    vm.change = function(item){
        vm.cur = item.id;
        setTimeout(function(){
            select_term();
        }, 500);
    }
});

function init_terminal(item){
    $('#'+item.id).terminal(function(command, term) {
        if (command == 'clear')
            term.clear()
        else{
//            term.pause();
            socket.emit('cmd', {'cmd':command, 'cwd':item.cwd, 'id':item.id});
        }
    }, { prompt: '> '
        , height: 400
        , greetings: false
        , name: item.id
        , outputLimit: {{=outputLimit}}
        , login: function(user, password, authenticate) {
            socket.emit('login', {'user':user, 'password':password, 'id':item.id});
            socket.on('logined', function(data){
                authenticate(data.token);
                item.cwd = data.output;
                var term = get_term(data.id);
                term.set_prompt(item.cwd + '> ');
            });
        }
    });
}

setTimeout(function(){
    init_terminal(model.shells[0])
}, 500);

$(window).bind("beforeunload", function() {
    socket.disconnect();
});

