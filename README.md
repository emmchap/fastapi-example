# Owkin techical test

## Introduction

This project was created in order to answer to a techical test for Owkin.

This application uses these python modules:
* FastAPI (with Uvicorn)
* SQLAlchemy (with an SQLite database)
* Requests

The docker scan is done with Snyk.

The dockers are runs with these parameters to be safe:
* Launch as a non-root user.
* Isolated network for each job.
* Read only mode for the volumes.
* Mount with an unique file instead of a directory.
* Limited resources usage with cgroup.

## Prerequisites

The most trusted way to run the application is to use the VSCode remote container development, with a DIND approach and pipenv.

These tools must be installed:
* VSCode (with the extension **Remote - Containers**)
* Docker

You also need a Snyk account.

Then follow these steps:
1. Copy the file *env.sample* to *.env*, and change $SNYK_TOKEN by your Snyk API token.
2. Reopen your project in a container with VSCode.
3. Install your virtual environment: ```pipenv install --dev```

## Launch your application

The application can be launched with this script: ```bash app.sh```

Then you can see your API swagger in this URL: http://localhost:8080/docs.

The test app.test.test_000_app.test_job_creation shows a workflow example to launch a job.

## Test your application

**Important**: this step must be done in a separated terminal session with the API turning in background, due to thread conflict with SQLite.

You can launch the tests with script: ```bash test.sh```

This will launch the pylint and mypy linters, and then the unit tests.

## What's next?

If I had more time, I would add these features:
* Use a real relationnal database (like MariaDB).
* Add an OAuth authentication mechanism with a JWT.
* Be able to kill a job.
* Display the error message in addition to the status.
* Create a CI/CD workflow that deploys a python package at the end.