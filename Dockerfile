FROM python:3.10
WORKDIR /app

SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]

ENV PYTHON_UNBUFFERED=1
ENV PATH=${PATH}:/root/.local/bin


RUN curl -sSL https://install.python-poetry.org | python3 -

COPY ./poetry.lock ./pyproject.toml ./

RUN poetry config virtualenvs.create false && poetry install --no-root --no-ansi --no-interaction

COPY README.md ./

COPY invisible /app/invisible

RUN poetry install --no-interaction --no-ansi

COPY main.py .

ENTRYPOINT [ "hypercorn", "--reload", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "main:app" ]