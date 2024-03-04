FROM python:3.11.6-slim-bookworm

ENV PORT=8000
EXPOSE 8000

# Prepare a non-root user
RUN adduser --system work
WORKDIR /home/work/app

RUN mkdir data; chown work data
RUN python -m venv .venv
RUN chown work .venv

ENV PATH="/home/work/app/.venv/bin:$PATH"
ENV HOME="/home/work"

COPY ./requirements.txt requirements.txt

ENV USE_CUDA=0
RUN apt update && apt install -y curl
RUN curl -o torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl http://download.pytorch.org/whl/cpu/torch-2.1.1%2Bcpu-cp311-cp311-linux_x86_64.whl#sha256=d83b13cb17544f9851cc31fed197865eae0c0f5d32df9d8d6d8535df7d2e5109
RUN pip install --upgrade pip
RUN pip install -U  torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl
RUN rm -rf          torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl

RUN echo "USE_CUDA=$USE_CUDA"
RUN pip install -Ur requirements.txt

COPY  bao/ bao
COPY *.yaml *.md ./
RUN chown work bao *.yaml *.md
RUN openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=US/ST=New York/L=Brooklyn/O=himalaya_dc Company/CN=himalaya_dc.com"
ENV PYTHONPATH="$PYTHONPATH:/home/work/app/"
ENV TRANSFORMERS_CACHE=/home/work/app/data/models/.cache
USER work
ENTRYPOINT python -m bao