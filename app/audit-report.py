# This file is part of Guardian.
#
# Guardian is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Guardian is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Guardian. If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import time
import uvicorn
import logging
import argparse
import pandas as pd
from io import StringIO
from dotenv import load_dotenv
# We specify the environment to be used.
load_dotenv(stream=StringIO("ENV=prod"))
from multiprocessing import Process
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import add_routes
from schema.util import GuardianRoleEnum, ApiPermissionEnum, ROLE_PERMISSION_MAPPING

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

# We set up a basic logger.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Guardian API")
add_routes(app)


def run_app():
    """
    Run the FastAPI app.
    """
    uvicorn.run(app, reload=False, port=8090, host="127.0.0.1")


def create_openapi_dataframe() -> pd.DataFrame:
    """
    Create a pandas DataFrame from the OpenAPI specification.
    """
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    result = []
    openapi = response.json()
    for path, content in openapi["paths"].items():
        for method, details in content.items():
            scopes = []
            for security in details.get("security", []):
                for value in security.values():
                    scopes.extend(value)
            read_scope = any([item.endswith("_read") for item in scopes])
            delete_scope = any([item.endswith("_delete") for item in scopes])
            create_scope = any([item.endswith("_create") for item in scopes])
            update_scope = any([item.endswith("_update") for item in scopes])
            result.append({
                "Method": method.upper(),
                "Tags": ", ".join(details.get("tags", [])),
                "Path": path,
                "Summary": details.get("summary"),
                "Description": details.get("description"),
                "Scopes": ", ".join(scopes) if scopes else None,
                "Scope Count": len(scopes),
                "Potential Issue": (method == "get" and not read_scope) or
                                   (method == "delete" and not delete_scope) or
                                   (method == "post" and not create_scope) or
                                   (method == "put" and not update_scope),
                "Read Scope": read_scope,
                "Delete Scope": delete_scope,
                "Create Scope": create_scope,
                "Update Scope": update_scope
            })
    return pd.DataFrame(result)


def create_roles_dataframe() -> pd.DataFrame:
    """
    Create a pandas DataFrame from the GuardianRoleEnum.
    """
    result = []
    for scope in ApiPermissionEnum:
        row = {"Scope": scope.name, "Description": scope.value}
        for role in GuardianRoleEnum:
            row[role.name] = scope.name in ROLE_PERMISSION_MAPPING[role.name]
        result.append(row)
    return pd.DataFrame(result).set_index("Scope")


def main(args: argparse.Namespace):
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    # Check target file
    path_name = os.path.dirname(args.output)
    logger.info("Creating reports")
    if not os.path.isdir(path_name):
        raise NotADirectoryError("Directory of output file does not exist.")
    # Start web server
    logger.info("Starting web server")
    p = Process(target=run_app)
    p.start()
    time.sleep(10)
    # Create reports
    with pd.ExcelWriter(args.output) as writer:
        for scope in args.type:
            if scope == "roles":
                df = create_roles_dataframe()
                df.to_excel(writer, sheet_name=scope)
            elif scope == "scopes":
                df = create_openapi_dataframe()
                df.to_excel(writer, sheet_name=scope, index=False)
            else:
                raise NotImplementedError()
    # Terminate web server
    logger.info("Terminating web server")
    p.terminate()
    p.join()
    logger.info("Finished")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate audit reports')
    parser.add_argument(
        '-t', '--type',
        type=str,
        nargs="+",
        required=True,
        choices=["scopes", "roles"],
        help='Type of report to generate'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output file'
    )
    try:
        main(parser.parse_args())
    except Exception as ex:
        logger.exception(ex)
