"""The job worker script."""

from os import chdir, getuid
from os.path import dirname, basename
from pathlib import Path
from json import load
from subprocess import run
from datetime import datetime
from requests import JSONDecodeError, Session  # type: ignore

job_dir = dirname(__file__)
job_id = basename(job_dir)
chdir(job_dir)
session = Session()
base_url = "http://localhost:8080"


def log(message: str):
    """Logs a message in the stdout."""
    print(f"{datetime.now()} - {job_id.split('-')[0]}: {message}")


def update_job(status: str, result: float | None = None, raise_error: bool = True):
    update = session.post(f"{base_url}/job/update", json={
        "id": job_id,
        "status": status,
        "result": result
    })
    assert update.status_code == 200
    if status == "FAILED" and raise_error:
        raise ValueError("Failed job")


update_job("RUNNING")
log("Created job directory")


output = run([
    "docker",
    "build",
    "-t",
    f"job_runner:{job_id}",
    "."
], capture_output=True)
if output.returncode > 0:
    log(f"Got this error while creating the dockerfile: {str(output.stderr)}")
    update_job("FAILED")
log("Image built")

output = run([
    "docker",
    "scan",
    "--accept-license",
    "--json",
    "--severity",
    "high",
    f"job_runner:{job_id}"
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

output_file = f"{job_dir}/perf.json"
Path(output_file).touch()
output = run([
    "docker",
    "network",
    "create",
    job_id
], capture_output=True)
if output.returncode > 0:
    log(
        f"got this error while creating the docker network: {str(output.stderr)}")
    update_job("FAILED")
log("Create isolated network")

log("Launching the job")
output = run([
    "docker",
    "run",
    "-v",
    f"{job_dir}/perf.json:/data/perf.json",
    "--user",
    f"{getuid()}",
    "--network",
    job_id,
    "--memory",
    "500M",
    "--cpus",
    "0.8",
    "--read-only",
    f"job_runner:{job_id}"
], capture_output=True)
try:
    with open(output_file) as finput:
        job_result = load(finput)
    update_job("FINISHED", job_result["perf"])
except (JSONDecodeError, KeyError) as error:
    log(f"got this error while fetching the results: {str(error.args)}")
    update_job("FAILED", raise_error=False)
    raise ValueError("Failed job") from error
log("Got the job results")

output = run([
    "docker",
    "network",
    "rm",
    job_id
], capture_output=True)
if output.returncode > 0:
    log(
        f"got this error while removing the docker network: {str(output.stderr)}")
    update_job("FAILED")
log("Removed the isolated network")

log("Finished job")
