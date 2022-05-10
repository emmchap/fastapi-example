"""The main application script."""

from os import getcwd, makedirs, getenv
from os.path import dirname
from shutil import rmtree, copy
from subprocess import Popen, run
from uuid import uuid4
from typing import List
from enum import Enum
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy import create_engine
from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy.orm import sessionmaker, Session  # type: ignore
from sqlalchemy import (  # type: ignore
    Column,
    String,
    Float
)
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module


logged_in = run([
    "docker",
    "scan",
    "--accept-license",
    "--login",
    "--token",
    f"{getenv('SNYK_TOKEN')}"
], capture_output=True)
if logged_in.returncode > 0:
    raise ValueError("Could not authenticate to snyk for docker image scanning")


app = FastAPI()

base = declarative_base()
engine = create_engine(f"sqlite:///{getcwd()}/db.db")
session = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


def db_session():
    """The session to work with."""
    db_sess = session()
    try:
        yield db_sess
    finally:
        db_sess.close()


class ModelJob(base):  # type: ignore
    """The job model class."""
    __tablename__ = "jobs"
    id = Column(String, default=uuid4, primary_key=True)
    status = Column(String, nullable=False, default="INIT")
    result = Column(Float)


class JobStatus(str, Enum):
    INIT = "INIT"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    FINISHED = "FINISHED"


class SchemaJob(BaseModel):  # pylint: disable=too-few-public-methods
    """The job schema class."""
    id: str = Field(uuid4(), description="The job ID.")
    status: JobStatus = Field(JobStatus.INIT, description="The job status.")
    result: float | None = Field(None, description="The job results.")

    class Config:  # pylint: disable=too-few-public-methods
        """Specific configuration."""
        orm_mode = True


class NotFound(BaseModel):  # pylint: disable=too-few-public-methods
    """The not found schema"""
    detail: str = Field("Item not found.",
                        description="The error detail message.")


ModelJob.metadata.drop_all(bind=engine)
ModelJob.metadata.create_all(bind=engine)
JOB_DIR = f"{getcwd()}/jobs"
rmtree(JOB_DIR, ignore_errors=True)


@app.get(
    "/job/{job_id}",
    response_model=SchemaJob,
    response_description="The job details.",
    responses={
        404: {"model": NotFound, "description": "The job was not found."}
    }
)
def get_job_details(job_id: str, database: Session = Depends(db_session)):
    """Allows to get the job details from a given ID."""
    job: ModelJob = database.query(ModelJob).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get(
    "/jobs",
    response_model=List[str],
    response_description="The list of job IDs."
)
def get_job_ids(database: Session = Depends(db_session)):
    """Allows to get all the job IDs."""
    job_ids: List[str] = []
    for job in database.query(ModelJob):
        job_ids.append(job.id)
    return job_ids


@app.post(
    "/job/create",
    response_model=SchemaJob,
    response_description="The job details."
)
def start_job(
    dockerfile: UploadFile = File(..., description="The Dockerfile to use"),
    database: Session = Depends(db_session)
):
    """Allows to start a job."""
    new_job = ModelJob(id=str(uuid4()))
    database.add(new_job)
    database.commit()
    job_dir = f"{JOB_DIR}/{new_job.id}"
    makedirs(job_dir)
    content = dockerfile.file.read()
    with open(f"{job_dir}/Dockerfile", "wb") as foutput:
        foutput.write(content)
    copy(f"{dirname(__file__)}/job.py", job_dir)
    Popen(["python", f"{job_dir}/job.py"])
    return new_job


@app.post(
    "/job/update",
    response_model=SchemaJob,
    response_description="The updated job details.",
    responses={
        404: {"model": NotFound, "description": "The Job was not found."}
    }
)
def update_job(
    data: SchemaJob,
    database: Session = Depends(db_session)
):
    """Allows to update a job."""
    job: ModelJob = database.query(ModelJob).get(data.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = data.status
    job.result = data.result
    database.commit()
    return job
