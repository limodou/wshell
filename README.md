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

```
python gevent_socketio_handler.py
```

## 浏览器要求

建议使用支持html5浏览器，chrome, firefox

## 版权声明

本软件使用 MIT 协议发布