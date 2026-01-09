# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:alpine3.22
#FROM python:slim

# Build argument for version
ARG VERSION=dev

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PATH="/root/.local/bin:${PATH}"

# Install system requirement
RUN apk add --no-cache -u p7zip file curl jq
#RUN apt-get update && apt-get install p7zip unrar

RUN curl -LsSf https://api.github.com/repos/EDM115/unrar-alpine/releases/latest \
    | jq -r '.assets[] | select(.name == "unrar") | .id' \
    | xargs -I {} curl -LsSf https://api.github.com/repos/EDM115/unrar-alpine/releases/assets/{} \
    | jq -r '.browser_download_url' \
    | xargs -I {} curl -Lsf {} -o /tmp/unrar && \
    install -v -m755 /tmp/unrar /usr/local/bin

# You MUST install required libraries or else you'll run into linked libraries loading issues
RUN apk add --no-cache libstdc++ libgcc

# Install uv and Python requirements
WORKDIR /app

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv --version \
    && uv sync

ADD src /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Update version in __init__.py
RUN sed -i "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" /app/automateddl/__init__.py

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
#RUN useradd appuser && chown -R appuser /app
# alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "main.py"]
