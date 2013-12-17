/******************************************************
 * Author: limodou@gmail
 ******************************************************/

version = '1.0'

function S4(){   
   return (((1+Math.random())*0x10000)|0).toString(16).substring(1);   
}    
function getId(){   
   return '_'+S4()+S4();   
}

WEB_SOCKET_SWF_LOCATION = "/static/WebSocketMain.swf";
WEB_SOCKET_DEBUG = true;

/* download process */
(function($){
    $(function(){
        jQuery('<iframe src="" style="display:none" id="ajaxiframedownload"></iframe>')
        .appendTo('body');
    });
    $.download = function(url){
    	//url and data options required
    	if(url){ 
    		//send request
            var el = $('#ajaxiframedownload');
            el.attr('src', url);
    	};
    };
})(jQuery);

var socket = io.connect('/shell');

function select_term(id){
    var term = get_term(id);
    term.focus(true);
//    term.scroll(1000);
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

//socket.on('connect', function(){
//    console.log('connect');
//});
socket.on('return', function(data){
    var term = get_term(data.id);
    term.echo(data.output);
//    term.resume();
});
socket.on('cwd', function(data){
    var term = get_term(data.id);
    term.set_prompt(make_prompt(data.output));
    var item = get_item(data.id);
    item.cwd = data.output;
//    term.resume();
});
socket.on('download', function(data){
    $.download(data.output);
});
socket.on('err', function(data){
    var term = get_term(data.id);
    term.error(data.output);
});
socket.on('needlogin', function(data){
    var term = get_term(data.id);
    term.error(data.output);
    term.logout();
});
//socket.on('disconnect', function(){
//    console.log('disconnect');
//});

avalon.config({
   interpolate: ["{%", "%}"]
});

var _id = getId();
var model = avalon.define("shell", function(vm){
    vm.shells = [{title:_id, id:_id, url:'/shell?id=' + _id, cwd:''}];
    vm.cur = _id;
    vm.newSession = function(){
        var _id = getId();
        var title = _id;
        vm.shells.push({title:title, url:'/shell?id=' + _id, id:_id, cwd:''});
        setTimeout(function(){
            init_terminal(model.shells[model.shells.length-1]);
            select_term();
        }, 500);
        vm.cur = _id;
    }
    vm.close = function(id){
        for(var i=0; i<vm.shells.length; i++){
            var x = vm.shells[i];
            if (x.id == id){
                vm.shells.splice(i, 1);
                break;
            }
        }
    }
    vm.change = function(item){
        vm.cur = item.id;
        setTimeout(function(){
            select_term();
        }, 500);
    }
});

function make_prompt(p){
    return '[[;#6c6;]'+p+'] ';
}
function init_terminal(item){
    $('#'+item.id).terminal(function(command, term) {
//       term.pause();
        if(command == 'close'){
            model.close(item.id);
        }else
            socket.emit('cmd', {'cmd':command, 'cwd':item.cwd, 'id':item.id});
    }, { prompt: make_prompt('>')
        , height: 400
        , greetings: false
        , name: item.id
        , outputLimit: 5000
        , login: function(user, password, authenticate) {
            socket.emit('login', {'user':user, 'password':password, 'id':item.id});
            socket.once('logined', function(data){
                authenticate(data.token);
                if (data.token){
                    item.cwd = data.output;
                    var term = get_term(data.id);
                    term.set_prompt(make_prompt(item.cwd));
                    
                    //add dropzone support
                    var drop = new Dropzone('#'+item.id, { 
                        url: "/upload?id="+item.id
                        , clickable: false
                        , previewsContainer: '.preview'
                        , success: function(file, r){
                            term.echo(term.get_prompt() + 'upload '+file.name)
                            if (r.success){
                                term.echo('Upload successful! The file is saved to '+r.filename)
                            }
                            else {
                                term.error(r.message);
                            }
                        }
                    });
                    item.drop = drop;
                    drop.on('sending', function(file, xhr, formData){
                        formData.append('path', item.cwd);
                    });
                }
            });
        }
        , onBeforelogout: function(term){
            item.drop.destroy();
            delete item.drop;
        }
        
    });
}

setTimeout(function(){
    init_terminal(model.shells[0])
}, 500);

$(window).bind("beforeunload", function() {
    socket.disconnect();
});

/* dropzone process */
Dropzone.autoDiscover = false;
