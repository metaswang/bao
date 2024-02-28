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

COPY ./requirements.txt requirements.txt
RUN pip install -Urq requirements.txt

COPY --chown=work bao/ bao
COPY --chown=work *.yaml *.md ./

ENV PYTHONPATH="$PYTHONPATH:/home/work/app/"

USER work
ENTRYPOINT python -m bao