FROM arm64v8/python:3.10-slim
WORKDIR /usr/src/app
COPY . .
LABEL authors="Kassiel Moreira"

ENTRYPOINT ["top", "-b"]