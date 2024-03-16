#!/usr/bin/env python3

"""Interact with HackerOne Hacker API.


First generate an API token through the Hackerone website and initialize the class:

username = "YOUR_USER_NAME"
token = "GENERATE_AN_API_TOKEN_THROUGH_HACKERONE_WEBSITE"
session = HackerOneSession(username, token)
"""
import pickle
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from time import sleep
from typing import Optional, Set

import requests
from rich.pretty import pprint

error_msg = f"[bold][white][[red]![/red][white]][/white][/bold]"
success_msg = f"[bold][white][[green]*[/green][white]][/white][/bold]"
info_msg = f"[bold][white][[blue]*[/blue][white]][/white][/bold]"

class Utils:

    @staticmethod
    def sizeof_fmt(num: float, suffix="B") -> str:
        # Accepts a float and returns a string with a human-readable string
        for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"


class HackerOneAssetType(Enum):
    """Class representing known types in HackerOne assets."""

    URL = "URL"
    OTHER = "OTHER"
    GOOGLE_PLAY_APP_ID = "GOOGLE_PLAY_APP_ID"
    APPLE_STORE_APP_ID = "APPLE_STORE_APP_ID"
    WINDOWS_APP_STORE_APP_ID = "WINDOWS_APP_STORE_APP_ID"
    CIDR = "CIDR"
    SOURCE_CODE = "SOURCE_CODE"
    DOWNLOADABLE_EXECUTABLES = "DOWNLOADABLE_EXECUTABLES"
    HARDWARE = "HARDWARE"
    OTHER_APK = "OTHER_APK"
    OTHER_IPA = "OTHER_IPA"
    TESTFLIGHT = "TESTFLIGHT"

@dataclass
class HackerOneAsset:
    """Class representing an asset of a HackerOne Program."""

    id: str

    type: HackerOneAssetType
    identifier: str
    eligible_for_bounty: bool
    eligible_for_submission: bool
    max_severity: str
    created_at: datetime
    updated_at: datetime

    instuction: Optional[str]
    reference: Optional[str]
    confidentiality_requirement: Optional[str]
    integrity_requirement: Optional[str]
    availability_requirement: Optional[str]

    def __repr__(self) -> str:
        """Pretty representation of class instance."""
        return f"<HackerOneAsset {self.type} {len(self.identifier)}>"

    @classmethod
    def load_from_dict(cls, asset_dict: dict):
        """Initialize class instance from Dictionary object."""
        return cls(
            asset_dict["id"],
            HackerOneAssetType(asset_dict["attributes"]["asset_type"]),
            asset_dict["attributes"]["asset_identifier"],
            asset_dict["attributes"]["eligible_for_bounty"],
            asset_dict["attributes"]["eligible_for_submission"],
            asset_dict["attributes"]["max_severity"],
            datetime.fromisoformat(asset_dict["attributes"]["created_at"].rstrip("Z")),
            datetime.fromisoformat(asset_dict["attributes"]["updated_at"].rstrip("Z")),
            asset_dict["attributes"].get("instruction"),
            asset_dict["attributes"].get("reference"),
            asset_dict["attributes"].get("confidentiality_requirement"),
            asset_dict["attributes"].get("integrity_requirement"),
            asset_dict["attributes"].get("availability_requirement"),
        )

    def __hash__(self):
        """Allow for use in Python Sets."""
        return hash(self.id)

    def __eq__(self, other):
        """Compare two class instances."""
        if other.id == self.id:
            return True
        return False

@dataclass
class HackerOneAttachment:
    """Class representing a single HackerOne Attachment."""

    id: int
    attachment_type: str
    expiring_url: str
    created_at_dt: datetime
    file_name: Path
    content_type: str
    file_size_bytes: int
    file_size_human: str
    local_path: Path

    def __repr__(self) -> str:
        """Pretty representation of class instance."""
        return f"<HackerOneAttachment {self.file_name}, {self.file_size_human}>"

    def download_attachment(self, save_dir_path: Path = Path("/tmp/h1_attachments/")):
        # Create directory if it doesn't exist
        if not save_dir_path.exists():
            save_dir_path.mkdir(parents=True)

        # Create full path
        attachment_full_path = save_dir_path.joinpath(self.file_name)

        # Getting file
        session = requests.session()
        with session.get(self.expiring_url) as resp:
            # Open file and save to disk
            with open(attachment_full_path, 'wb') as f:
                f.write(resp.content)

        self.local_path = save_dir_path

        return save_dir_path

    @classmethod
    def load_from_dict(cls, attachment):
        if attachment["type"] != "attachment":
            raise "The data provided is not type 'attachment'"

        if "id" in attachment:
            attachment_id = attachment["id"]
        else:
            raise Exception(f"No report ID")

        attachment_type = attachment["type"],
        expiring_url = attachment["attributes"]["expiring_url"]
        created_at_dt = datetime.fromisoformat(attachment["attributes"]["created_at"])
        file_name = attachment["attributes"]["file_name"]
        content_type = attachment["attributes"]["content_type"]
        file_size_bytes = attachment["attributes"]["file_size"]
        file_size_human = Utils.sizeof_fmt(file_size_bytes)
        local_path = None

        return cls(
            attachment_id,
            attachment_type,
            expiring_url,
            created_at_dt,
            file_name,
            content_type,
            file_size_bytes,
            file_size_human,
            local_path
        )


@dataclass
class HackerOneReport:
    """Class representing a single HackerOne Report."""

    id: int

    # Report attributes
    report_title: str
    formatted_report_title: str
    reporter: str
    reporter_url: str
    reporter_md_link: str
    weakness_name: str
    report_url: str
    original_report_body: str
    formatted_report_body: str
    reported_datetime: datetime
    raw_report_dict: dict

    def __repr__(self) -> str:
        """Pretty representation of class instance."""
        return f"<HackerOneReport {self.report_title}, {self.report_url}>"

    def _format_report(report):
        return (f"HackerOne Report: https://hackerone.com/reports/{report.id}\n"
                        f"Report Date: {report.reported_datetime}\n"
                        f"Reporter: {report.reporter_url}\n"
                        f"Weakness: {report.weakness_name}\n"
                        f"{report.original_report_body}")

    @classmethod
    def load_from_dict(cls, report):
        if report["data"]["type"] != "report":
            raise "The data provided is not type 'report'"

        # HackerOne API does not reply with any information if the field is not populated
        # i.e. no weakness = no value but if weakness is set, the field exists

        if "id" in report["data"]:
            report_id = report["data"]["id"]
        else:
            raise Exception(f"No report ID")

        if "title" in report['data']['attributes']:
            report_title = report['data']['attributes']['title']
        else:
            raise Exception(f"No report title")

        if "username" in report["data"]["relationships"]["reporter"]["data"]["attributes"]:
            reporter_username = report['data']['relationships']['reporter']['data']['attributes']['username']
        else:
            # pprint(report["data"]["relationships"]["reporter"]["data"]["attributes"])
            raise Exception(f"No reporter username")

        if "weakness" in report["data"]["relationships"]:
            weakness = report["data"]["relationships"]["weakness"]["data"]["attributes"]["name"]
        else:
            weakness = None

        if "vulnerability_information" in report["data"]["attributes"]:
            report_body = report["data"]["attributes"]["vulnerability_information"]
        else:
            raise Exception(f"No report body found")

        report_submitted_dt = datetime.fromisoformat(report["data"]["attributes"]["submitted_at"])


        return cls(
            report_id,
            report_title,
            f"[HackerOne] {report_title}",
            reporter_username,
            f"https://hackerone.com/{reporter_username}",
            f"[{reporter_username}](https://hackerone.com/{reporter_username})",
            weakness,
            f"https://hackerone.com/reports/{report_id}",
            report_body,
            (f"HackerOne Report: https://hackerone.com/reports/{report_id}\n"
                        f"Report Date: {report_submitted_dt},\n"
                        f"Reporter URL: https://hackerone.com/{reporter_username}\n"
                        f"Weakness: {weakness}\n"
                        f"{report_body}"),
            report_submitted_dt,
            report
        )

    def h1_bug_converter(self, bzapi):
        """Consume report data and produce a Bugzilla report"""
        title_prefix = f"[HackerOne Report]"
        product = "Websites"
        component = "Other"
        groups =["websites-security"]

        create_info = bzapi.build_createbug(product=product, component=component, summary=self.formatted_report_title,
                                        groups=groups, description=self.formatted_report_body)
        create_info["type"] = "defect"

        return create_info



@dataclass
class HackerOneProgram:
    """Class representing a single HackerOne Program."""

    id: str

    # Program attributes
    handle: str
    name: str
    currency: str
    profile_picture: str
    submission_state: str
    triage_active: str
    state: str
    started_accepting_at: datetime
    number_of_reports_for_user: int
    number_of_valid_reports_for_user: int
    bounty_earned_for_user: float
    last_invitation_accepted_at_for_user: Optional[str]
    bookmarked: bool
    allows_bounty_splitting: bool
    offers_bounties: bool

    # Assets
    assets: Set[HackerOneAsset]

    def __repr__(self) -> str:
        """Pretty representation of class instance."""
        return f"<HackerOneProgram {self.name}, {len(self.assets)} assets>"

    @property
    def program_url(self) -> str:
        """The URL to the program on HackerOne."""
        return f"https://hackerone.com/{self.handle}?type=team"

    @classmethod
    def load_from_dict(cls, program_dict: dict):
        """Initialize class instance from Dictionary object."""

        try:
            assets = {
                HackerOneAsset.load_from_dict(asset)
                for asset in program_dict["relationships"]["structured_scopes"]["data"]
            }
        except KeyError:
            # When listing programs the assets are not returned.
            assets = set()

        return cls(
            program_dict["id"],
            program_dict["attributes"]["handle"],
            program_dict["attributes"]["name"],
            program_dict["attributes"]["currency"],
            program_dict["attributes"]["profile_picture"],
            program_dict["attributes"]["submission_state"],
            program_dict["attributes"]["triage_active"],
            program_dict["attributes"]["state"],
            datetime.fromisoformat(
                program_dict["attributes"]["started_accepting_at"].rstrip("Z")
            ),
            program_dict["attributes"]["number_of_reports_for_user"],
            program_dict["attributes"]["number_of_valid_reports_for_user"],
            program_dict["attributes"]["bounty_earned_for_user"],
            program_dict["attributes"]["last_invitation_accepted_at_for_user"],
            program_dict["attributes"]["bookmarked"],
            program_dict["attributes"]["allows_bounty_splitting"],
            program_dict["attributes"]["offers_bounties"],
            assets,
        )

    def __hash__(self):
        """Allow for use in Python Sets."""
        return hash(self.id)

    def __eq__(self, other):
        """Compare two class instances."""
        if other.id == self.id:
            return True
        return False


class HackerOneSession:
    """Class to interact with the Hacker API of HackerOne."""

    def __init__(self, username, token, console, version="v1", local_cache_path: Path = Path("/tmp/h1_cache"),
                 cache: bool = False, retry_time: int = 5):
        self._session = requests.session()
        self.version = version

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._session.auth = (username, token)
        self._session.headers.update(headers)
        self._console = console
        self._local_cache_path = local_cache_path
        self._cache = cache
        self._retry_time = retry_time

    def _get(self, endpoint, params: dict = None):
        """Retrieve a HTTP GET endpoint."""
        url = self._url(endpoint)

        # Retry loop
        while True:
            response = self._session.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                self._console.print(f"{error_msg} Permission denied. That report is not accessable with this API key. HTTP Error {int(403)}")
                sys.exit(1)
            else:
                self._console.print(f"{info_msg} Got error {response.status_code} back, retrying in {self._retry_time} seconds")
                sleep(self._retry_time)

    def _url(self, endpoint) -> str:
        """Generate full API url."""
        url = f"https://api.hackerone.com/{self.version}/{endpoint}"
        return url

    def list_programs(self) -> Set[HackerOneProgram]:
        """Retrieve a list of programs."""
        endpoint = "programs"

        programs = set()

        page_number = 1
        while True:
            response = self._get(endpoint, params={"page[number]": page_number})

            if not response["links"].get("next") or not response.get("data"):
                break
            else:
                page_number += 1

                programs.update(
                    [
                        HackerOneProgram.load_from_dict(program)
                        for program in response["data"]
                    ]
                )

        return programs

    def get_program(self, program_handle) -> HackerOneProgram:
        """Retrieve a program by handle."""
        endpoint = f"programs/{program_handle}"
        response = self._get(endpoint)

        return HackerOneProgram.load_from_dict(response)

    def get_assets(self, program_handle) -> Set[HackerOneAsset]:
        """Get the assets of given program.

        This is a helper function to return only the assets on a program. Useful
        when you have retrieved a list of programs as this doesn't include assets.
        """
        endpoint = f"programs/{program_handle}"
        response = self._get(endpoint)

        try:
            assets = {
                HackerOneAsset.load_from_dict(asset)
                for asset in response["relationships"]["structured_scopes"]["data"]
            }
        except KeyError:
            # When listing programs the assets are not returned.
            assets = set()

        return assets

    def get_report(self, report_id: int) -> HackerOneReport:
        """Get the report at an ID"""
        # This function only gets reports from H1 or from the cache
        # For development, caching can be enabled to not be banned for too many requests of the same report over and over
        endpoint = f"reports/{report_id}"

        if self._local_cache_path.exists() and self._cache:
            # Path exists and caching is desired
            self._console.print(f"{info_msg} Using the local cache")
            with open(self._local_cache_path, 'rb') as f:
                report_dict = pickle.load(f)

            if report_id not in report_dict:
                # Get the report if missing
                self._console.print(f"{info_msg} Local cache found, report ID not found, getting")
                report = self._get(endpoint)

                # Add to cache
                report_dict = {report_id: report}
                # Write report to pickle
                with open(self._local_cache_path, 'wb') as f:
                    pickle.dump(report_dict, f)
                return HackerOneReport.load_from_dict(report=report_dict[report_id])

            else:
                self._console.print(f"{success_msg} Report found in local cache")
                return HackerOneReport.load_from_dict(report=report_dict[report_id])
        elif not self._local_cache_path.exists() and self._cache:
            # Path does not exist and caching is desired
            if self._cache:
                self._console.print(f"{info_msg} Local cache doesn't exist but it is desired, contacting server to warm up the cache")
            report = self._get(endpoint)
            # Add to cache
            report_dict = {report_id: report}

            # Write report to pickle
            with open(self._local_cache_path, 'wb') as f:
                pickle.dump(report_dict, f)
            return HackerOneReport.load_from_dict(report=report_dict[report_id])

        elif not self._cache:
            # Local caching set to false
            report = self._get(endpoint)
            # Add to cache
            report_dict = {report_id: report}
            return HackerOneReport.load_from_dict(report=report_dict[report_id])

    def get_attachments(self, report: HackerOneReport) -> [HackerOneAttachment]:
        """Get all attachment information in a report"""
        attachments_list = list()
        raw_dict = report.raw_report_dict
        attachment_list = list()

        # Get attachments for each comment
        for activity in raw_dict["data"]["relationships"]["activities"]["data"]:

            # Activities that may have attachements
            # I don't think we want to import "activity-report-triage-summary-created" as that would be a repeat of
            # the original report
            attachment_activity_types = ["activity-comment"]
            if activity["type"] in attachment_activity_types:
                # If the activity is 'internal', ignore it as we likely won't need to grab attachments from internal
                # comments
                message = activity["attributes"]["message"]

                # If internal is False
                if not activity["attributes"]["internal"]:
                    # If there's an attachment
                    if "attachments" in activity["relationships"]:
                        for attachment in activity["relationships"]["attachments"]["data"]:
                            h1_attachement = HackerOneAttachment.load_from_dict(attachment)
                            attachment_list.append(h1_attachement)

        return attachment_list
