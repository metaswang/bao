FROM python:3.11.6-slim-bookworm

ARG UID
ARG GID
ENV USER=$UID
ENV PORT=8000
EXPOSE 8000

# Prepare a non-root user
RUN adduser --system ${USER} --gid ${GID}
WORKDIR /home/${USER}/app

RUN mkdir data; chown -R ${USER} data
RUN mkdir data/models; chown -R ${USER} data/models
RUN python -m venv .venv
RUN chown ${USER} .venv

ENV PATH="/home/${USER}/app/.venv/bin:$PATH"
ENV HOME="/home/${USER}"

COPY ./requirements.txt requirements.txt

ENV USE_CUDA=0
RUN apt update && apt install -y curl
RUN curl -o torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl http://download.pytorch.org/whl/cpu/torch-2.1.1%2Bcpu-cp311-cp311-linux_x86_64.whl#sha256=d83b13cb17544f9851cc31fed197865eae0c0f5d32df9d8d6d8535df7d2e5109
RUN pip install --upgrade pip
RUN pip install -U  torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl
RUN rm -rf          torch-2.1.1+cpu-cp311-cp311-linux_x86_64.whl

RUN pip install -Ur requirements.txt

COPY  bao/ bao
COPY *.yaml *.md ./
RUN chown ${USER} bao *.yaml *.md

RUN chown -R  ${USER} data/qdrant_local
ENV PYTHONPATH="$PYTHONPATH:/home/${USER}/app/"
ENV TRANSFORMERS_CACHE=/home/${USER}/app/data/models/.cache
USER ${USER}
ENTRYPOINT python -m bao