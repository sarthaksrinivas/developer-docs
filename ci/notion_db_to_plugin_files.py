import os

os.chdir("/Users/ajaymerchia/wkspc/developer-docs")

import pandas as pd
import requests

df = pd.read_csv("./Plugin Research df47317a8eb449178020d6bf3dec4b23_all.csv")
from enum import Enum
from dataclasses import dataclass
from ci.data_utils import (
    load_yaml_data,
    replace_nan_with_none,
    deep_equal,
    dump_to_yaml_str,
    render_template_file,
)
from typing import List
from ci.model import *

import shutil

# CONSTANTS (Can change if we change the Notion DB Structure)


class NotionColumns(Enum):
    TITLE = "Title"
    DESCRIPTION = "Description"
    PURPLE_CHAT_LINK = "Purple Chat"
    FIDELITY = "Current Fidelity"
    CONTENT_TYPE = "Content Type"
    SLUG = "Slug"
    SYSTEM_SLUG = "System Slug"
    SOLUTION_TAGS = "Solutions Tags"
    SYSTEM_IMAGE = "System Image"
    CUSTOMER_DEPLOYMENTS = "Customers Deployed"


TEMPLATE_MAP = {Fidelity.IDEA: "idea.txt"}
TEMPLATES_DIR = "ci/templates"


class Record:
    def __init__(self, record: object) -> None:
        self._record = replace_nan_with_none(record)

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes(self._record[NotionColumns.CONTENT_TYPE.value])

    @property
    def fidelity(self) -> Fidelity:
        return Fidelity(self._record[NotionColumns.FIDELITY.value])

    @property
    def slug(self) -> str:
        return self._record[NotionColumns.SLUG.value]

    @property
    def record_directory(self) -> str:
        return os.path.join(DIRECTORY_MAP[self.content_type], record.slug)

    @property
    def record_readme(self) -> str:
        return os.path.join(self.record_directory, README_FILENAME)

    @property
    def front_matter(self) -> dict:
        return load_yaml_data(self.record_readme)

    @property
    def title(self) -> str:
        return self._record[NotionColumns.TITLE.value]

    @property
    def img_url(self) -> str:
        return self._record[NotionColumns.SYSTEM_IMAGE.value]

    @property
    def img_path(self) -> str:
        return os.path.join(self.record_directory, LOGO_FILE)

    @property
    def systems(self) -> List[str]:
        sys_slug_csv: str = self._record[NotionColumns.SYSTEM_SLUG.value]
        if not sys_slug_csv:
            raise ValueError(f"No system slugs defined for {self.title}")
        return sys_slug_csv.split(",")

    @property
    def solution_tags(self) -> List[str]:
        tags_csv: str = self._record[NotionColumns.SOLUTION_TAGS.value]
        return tags_csv.split(", ")

    @property
    def description(self) -> str:
        configured_description = self._record[NotionColumns.DESCRIPTION.value]
        if configured_description:
            return configured_description
        return None

        # Better to handle this logic in the front-end as a default
        # if self.content_type == ContentTypes.CONNECTOR:
        #     return f'Connect Creator Studio to {self.title}.'
        # elif self.content_type == ContentTypes.PLUGIN:
        #     return f'A new plugin for your copilot: {self.title}'

    @property
    def purple_chat_link(self) -> str:
        return self._record[NotionColumns.PURPLE_CHAT_LINK.value]

    @property
    def num_implementations(self) -> int:
        deployments: str = self._record[NotionColumns.CUSTOMER_DEPLOYMENTS.value]
        if not deployments:
            return 0
        
        return len(deployments.split(','))

    def to_front_matter(self) -> dict:
        if self.content_type == ContentTypes.CONNECTOR:
            return {
                "name": self.title,
                "description": self.description,
                "fidelity": self.fidelity.name,
                "num_implementations": self.num_implementations
            }
        elif self.content_type == ContentTypes.PLUGIN:
            return {
                "name": self.title,
                "description": self.description,
                "fidelity": self.fidelity.name,
                "systems": self.systems,
                "purple_chat_link": self.purple_chat_link,
                "solution_tags": self.solution_tags,
                "num_implementations": self.num_implementations,
            }
        else:
            raise NotImplementedError(f"No Front Matter for {self.content_type}")

    def to_front_matter_yaml(self) -> str:
        fm = self.to_front_matter()
        result_dict = {k: v for k, v in fm.items() if v is not None}
        return dump_to_yaml_str(result_dict)

    @property
    def template_filepath(self) -> str:
        return os.path.join(
            TEMPLATES_DIR, DIRECTORY_MAP[self.content_type], TEMPLATE_MAP[self.fidelity]
        )

    def render_template(self) -> str:
        render_dict = {
            "front_matter": self.to_front_matter_yaml(),
        }
        if self.content_type == ContentTypes.PLUGIN:
            render_dict["purple_chat_link"] = self.purple_chat_link

        result = render_template_file(self.template_filepath, render_dict)
        return result

def validate_file_consistent_with_notion(record: Record):
    # Ensure the front matter is AT LEAST the same
    stored_front_matter = record.front_matter
    for k, v in record.to_front_matter().items():
        if not v:
            # No expected value
            continue

        if k not in stored_front_matter:
            raise ValueError(
                f"Missing {k} in {record.record_readme} front matter. Recommended value: '{v}'"
            )
        if not deep_equal(stored_front_matter[k], v):
            raise ValueError(
                f'Stored value for {k} in {record.record_readme} was "{stored_front_matter[k]}". Expected "{v}"'
            )


def clear_directory(directory):
    if os.path.exists(record.record_directory):
        shutil.rmtree(record.record_directory)


def validate_record(record: Record):
    if not record.slug:
        return

    if record.fidelity in [Fidelity.TEMPLATE]:
        raise NotImplementedError("No support built for templates yet.")
    elif record.fidelity in [
        Fidelity.GUIDE,
        Fidelity.VALIDATED,
    ]:
        # Check if the guide file exists
        if not os.path.exists(record.record_readme):
            raise FileNotFoundError(
                f"Could not find a guide or research file for {record.record_directory}"
            )

        # Detect discrepancies with the guide file
        validate_file_consistent_with_notion(record)
    elif record.fidelity in [Fidelity.IDEA]:
        existing_image = None
        if os.path.exists(record.img_path):
            existing_image = open(record.img_path, "rb").read()

        clear_directory(record.record_directory)
        os.makedirs(record.record_directory)
        open(record.record_readme, "w+").write(record.render_template())
        # Add the logo
        if record.content_type == ContentTypes.CONNECTOR:
            if existing_image:
                open(record.img_path, "wb+").write(existing_image)
            elif record.img_url:
                response = requests.get(record.img_url)
                open(record.img_path, "wb+").write(response.content)
            else:
                raise ValueError(f"No Image for Connector: {record.slug}")

    elif record.fidelity in [Fidelity.IMPOSSIBLE]:
        clear_directory(record.record_directory)

    else:
        raise NotImplementedError(f"No support built for {record.fidelity} yet.")


errors = []

# Complain if there are any duplicate slugs.
slug_counts = df[NotionColumns.SLUG.value].value_counts()
if max(slug_counts.values) > 1:
    raise ValueError("Found duplicate slugs in CSV.", slug_counts)


for _, record in df.iterrows():
    record = Record(record=record)
    try:
        validate_record(record)
    except Exception as e:
        errors.append(e)

if errors:
    print(errors)
    raise errors[0]
