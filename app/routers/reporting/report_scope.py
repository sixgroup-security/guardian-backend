"""
This file defines and documents all FastAPI endpoints to manage a scope.
"""

from __future__ import annotations

import re
import logging
import ipaddress
from uuid import UUID
from typing import Annotated, List
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum, StatusMessage, StatusEnum, InvalidDataError, update_attributes
from schema.reporting.report_scope import ReportScope, ReportScopeCreate, ReportScopeRead, ReportScopeUpdate, AssetType
from routers.user import get_current_active_user, User
from routers.project import check_access_permission, get_project
from routers.reporting.report import API_REPORT_PREFIX

logger = logging.getLogger(__name__)

API_REPORT_SCOPE_PREFIX = API_REPORT_PREFIX + "/{report_id}/scope"

router = APIRouter(
    prefix=API_REPORT_SCOPE_PREFIX,
    tags=["report", "scope"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def check_input(asset_type: AssetType, asset: str) -> str:
    """
    Verifies the asset type.
    """
    result = asset.strip()
    if asset_type == AssetType.ip_address:
        try:
            ipaddress.ip_address(result)
        except ValueError:
            raise InvalidDataError("The asset contains an invalid IPv4/IPv6 address.")
    elif asset_type == AssetType.network_range:
        try:
            ipaddress.ip_network(result)
        except ValueError:
            raise InvalidDataError("The asset contains an invalid IPv4/IPv6 network range.")
    elif asset_type == AssetType.email_address:
        if not re.match(r"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$", result):
            raise InvalidDataError("The asset contains an invalid email address.")
    return result


@router.get("", response_model=List[ReportScopeRead])
def get_all_report_scopes(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.pentest_report_read.name])],
        project: Annotated[UUID, Depends(get_project)],
        report_id: UUID
):
    """
    Retrieve all scopes for a specific report.
    """
    check_access_permission(current_user, project)
    report = project.get_report(report_id, must_exist=True)
    return report.scopes


@router.post("", response_model=StatusMessage)
def create_report_scope(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.pentest_report_create.name])],
        project: Annotated[UUID, Depends(get_project)],
        report_id: UUID,
        item: Annotated[ReportScopeCreate, Body],
        session: Session = Depends(get_db)
):
    """
    Allows administrators and penetration testers to create a new report scope.
    """
    check_access_permission(current_user, project)
    try:
        asset = check_input(asset_type=item.type, asset=item.asset)
        if report := project.get_report(report_id):
            scope = ReportScope(**item.dict(exclude={"asset"}), report_id=report_id, asset=asset)
            session.add(scope)
            report.scopes.append(scope)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message="Scope successfully added."
        )
    except ValueError as ex:
        logger.exception(ex)
    except InvalidDataError as ex:
        raise ex
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("", response_model=StatusMessage)
def update_report_scope(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.pentest_report_update.name])],
        project: Annotated[UUID, Depends(get_project)],
        report_id: UUID,
        item: Annotated[ReportScopeUpdate, Body],
        session: Session = Depends(get_db)
):
    check_access_permission(current_user, project)
    try:
        asset = check_input(asset_type=item.type, asset=item.asset)
        if (report := project.get_report(report_id)) and (scope := report.get_scope(item.id)):
            item.asset = asset
            update_attributes(
                target=scope,
                source=item,
                source_model=ReportScopeUpdate
            )
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message="Scope successfully updated."
        )
    except ValueError as ex:
        logger.exception(ex)
    except InvalidDataError as ex:
        raise ex
    except Exception as e:
        raise InvalidDataError(str(e))


@router.delete("/{scope_id}", response_model=StatusMessage)
def delete_report_scope(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.pentest_report_delete.name])],
        project: Annotated[UUID, Depends(get_project)],
        report_id: UUID,
        scope_id: UUID,
        session: Session = Depends(get_db)
):
    """
    Allows administrators and penetration testers to delete an existing report scope.
    """
    check_access_permission(current_user, project)
    if (report := project.get_report(report_id)) and (scope := report.get_scope(scope_id)):
        session.delete(scope)
        session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message="Scope successfully deleted."
    )
