from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    username: str
    realname: str
    user_type: str
    password: str

@dataclass
class Project:
    id: Optional[int] = None
    project_no: Optional[str] = None
    name: Optional[str] = None
    project_type: Optional[str] = None
    client_name: Optional[str] = None
    market_leader: Optional[str] = None
    project_leader: Optional[str] = None
    progress: Optional[str] = None
    report_numbers: Optional[str] = None
    amount: Optional[float] = None
    is_paid: Optional[str] = None
    creator: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    contract_file: Optional[str] = None
    create_date: Optional[str] = None

@dataclass
class Report:
    id: Optional[int] = None
    report_no: Optional[str] = None
    project_id: Optional[int] = None
    file_paths: Optional[str] = None
    creator: Optional[str] = None
    create_date: Optional[str] = None
    reviewer1: Optional[str] = None
    reviewer2: Optional[str] = None
    reviewer3: Optional[str] = None
    signer1: Optional[str] = None
    signer2: Optional[str] = None
    files: Optional[List] = None

@dataclass
class ReportFile:
    id: Optional[int] = None
    report_id: Optional[int] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    uploader_username: Optional[str] = None
    uploader_realname: Optional[str] = None
    upload_time: Optional[str] = None
    file_size: Optional[int] = None