FROM continuumio/miniconda3

# 设置工作目录
WORKDIR /app

# 安装cron
RUN apt-get update && apt-get install -y cron

# 在安装cron后添加
RUN apt-get install -y tzdata
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 创建conda环境并安装基础包
RUN conda create -n myenv python=3.9 pip \
    && conda install -n myenv -c conda-forge ta-lib pandas numpy \
    && conda clean -afy

# 设置shell使用conda环境
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（添加-v参数查看详细输出）
RUN pip install -v --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || \
    (echo "pip install failed" && exit 1)

# 复制应用代码
COPY . .

# 设置crontab
RUN echo "0 17 * * * cd /app/app && /opt/conda/envs/myenv/bin/conda run -n myenv bash run_analysis.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/analysis-cron
RUN chmod 0644 /etc/cron.d/analysis-cron
RUN crontab /etc/cron.d/analysis-cron
RUN touch /var/log/cron.log

# 暴露端口
EXPOSE 5100

# 设置环境变量
ENV PATH /opt/conda/envs/myenv/bin:$PATH

# 设置工作目录
WORKDIR /app/app

# 启动命令：启动cron服务并运行应用
CMD service cron start && conda run --no-capture-output -n myenv python app.py