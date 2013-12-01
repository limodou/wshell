WSHELL
=========

一个可以在网页上访问shell的小工具，它基于以下技术或工具开发：

* uliweb
* gevent
* gevent-socketio
* socketio.js
* avalon.js 页面模板及动态更新
* jquery.terminal.js 前端终端功能组件
* semantic-ui 基础页面框架

## 主要功能特性

* 用户登录方可使用
* 支持开多个终端窗口
* 支持shell交互，如mysql的命令行支持
* download filename 可以下载某个文件，会自动进行权限检查，用户为运行WShell的用户
* upload 可以上传文件

## 安装要求

* uliweb
* gevent
* gevent-socketio

## 如何运行

测试

```
uliweb runserver --gevent-socketio
```

部署

使用 `gevent_socketio_handler.py`

## 配置说明

在 apps/server/settings.ini 提供了几个配置项，你可以在settings.ini中进行覆盖：

```
[WSHELL]
user = 'test'
password = 'test'
stop_interval = 30*60
login_path = '$PROJECT'
```

分别解释如下：

* `user`, `password` 用来标识用户名和口令。在打开一个对话时，会先要进行登录。
* `stop_interval` 在后台服务运行时，因为有些子进程可能是以交互的形式在工作，所以
  进程不会退出。但是如果长时间不用，会造成资源的消耗，所以后台程序会定时扫描
  没有数据交互的进程，如果达到超时时间，则会主动杀掉。缺省时间为30分钟。
* `login_path` 表示登录后返回给前端的路径。缺省为 `$PROJECT` 表示项目目录，即
  后台服务项目所在的目录。你可以修改为其它的起始目录。除 `$PROJECT` 外，还可以
  使用 `$HOME` 。

## 浏览器要求

建议使用支持html5浏览器，chrome, firefox

## 版权声明

本软件使用 MIT 协议发布