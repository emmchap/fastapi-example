"""The job worker script."""

from os import chdir, getuid
from os.path import dirname, basename
from pathlib import Path
from json import load, JSONDecodeError
from subprocess import run
from datetime import datetime
from requests import Session  # type: ignore

JOB_DIR = dirname(__file__)
JOB_ID = basename(JOB_DIR)
chdir(JOB_DIR)
session = Session()
BASE_URL = "http://localhost:8080"


def log(message: str):
    """Logs a message in the stdout."""
    print(f"{datetime.now()} - {JOB_ID.split('-')[0]}: {message}")


def update_job(status: str, result: float | None = None, raise_error: bool = True):
    """Updates a job status."""
    update = session.post(f"{BASE_URL}/job/update", json={
        "id": JOB_ID,
        "status": status,
        "result": result
    })
    assert update.status_code == 200
    if status == "FAILED" and raise_error:
        raise ValueError("Failed job")


update_job("RUNNING")
log("Created job directory")


output = run([  # pylint: disable=subprocess-run-check
    "docker",
    "build",
    "-t",
    f"job_runner:{JOB_ID}",
    "."
], capture_output=True)
if output.returncode > 0:
    log(f"Got this error while creating the dockerfile: {str(output.stderr)}")
    update_job("FAILED")
log("Image built")

output = run([  # pylint: disable=subprocess-run-check
    "docker",
    "scan",
    "--accept-license",
    "--json",
    "--severity",
    "high",
    f"job_runner:{JOB_ID}"
], capture_output=True)
if output.returncode > 0:
    if len(output.stderr) > 0:
        log(
            f"Got this error while scanning the docker image: {str(output.stdout)}")
    else:
        log(
            f"Found these vulnerabilities during the image scan: {str(output.stdout)}")
    update_job("FAILED")

log("Scanned image")

output_file = f"{JOB_DIR}/perf.json"
Path(output_file).touch()
output = run([  # pylint: disable=subprocess-run-check
    "docker",
    "network",
    "create",
    JOB_ID
], capture_output=True)
if output.returncode > 0:
    log(
        f"got this error while creating the docker network: {str(output.stderr)}")
    update_job("FAILED")
log("Create isolated network")

log("Launching the job")
output = run([  # pylint: disable=subprocess-run-check
    "docker",
    "run",
    "-v",
    f"{JOB_DIR}/perf.json:/data/perf.json",
    "--user",
    f"{getuid()}",
    "--network",
    JOB_ID,
    "--memory",
    "500M",
    "--cpus",
    "0.8",
    "--read-only",
    f"job_runner:{JOB_ID}"
], capture_output=True)
try:
    with open(output_file, encoding="utf-8") as finput:
        job_result = load(finput)
    update_job("FINISHED", job_result["perf"])
except (JSONDecodeError, KeyError) as error:
    log(f"got this error while fetching the results: {str(error.args)}")
    update_job("FAILED", raise_error=False)
    raise ValueError("Failed job") from error
log("Got the job results")

output = run([  # pylint: disable=subprocess-run-check
    "docker",
    "network",
    "rm",
    JOB_ID
], capture_output=True)
if output.returncode > 0:
    log(
        f"got this error while removing the docker network: {str(output.stderr)}")
    update_job("FAILED")
log("Removed the isolated network")

log("Finished job")
