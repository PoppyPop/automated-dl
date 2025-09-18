# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:alpine3.22
#FROM python:slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install system requirement
RUN apk add --no-cache -u p7zip file
#RUN apt-get update && apt-get install p7zip unrar

# Install pip requirements
ADD requirements.txt .
RUN python -m pip install -r requirements.txt



WORKDIR /app
ADD src /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
#RUN useradd appuser && chown -R appuser /app
# alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "main.py"]


