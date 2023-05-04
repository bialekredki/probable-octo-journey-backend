FROM python:3.10
WORKDIR /app

SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]

ENV PYTHON_UNBUFFERED=1
ENV PATH=${PATH}:/root/.local/bin
RUN  curl -fsSL https://apt.cli.rs/pubkey.asc | tee -a /usr/share/keyrings/rust-tools.asc
RUN curl -fsSL https://apt.cli.rs/rust-tools.list | tee /etc/apt/sources.list.d/rust-tools.list

RUN apt update && apt install -y watchexec-cli && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY ./poetry.lock ./pyproject.toml ./

RUN poetry config virtualenvs.create false && poetry install --no-root --no-ansi --no-interaction

COPY README.md ./

COPY app /app/app

RUN poetry install --no-interaction --no-ansi

COPY main.py .

ENTRYPOINT [ "hypercorn", "--reload", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "main:app" ]