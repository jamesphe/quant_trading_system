#!/bin/bash

# 启动cron服务
service cron start

# 启动主应用
conda run --no-capture-output -n myenv python app.py 