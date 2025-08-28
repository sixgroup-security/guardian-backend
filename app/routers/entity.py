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
# along with MyAwesomeProject. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
from uuid import UUID
from typing import List, Annotated
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import (
    ApiPermissionEnum, get_by_id, update_database_record, StatusEnum, StatusMessage, UserLookup, InvalidDataError,
    NotFoundError
)
from schema.entity import (
    Entity, ProviderRead, CustomerRead, ProviderCreate, CustomerCreate, ProviderUpdate, CustomerUpdate, EntityRoleEnum
)
from routers.user import User, get_current_active_user, get_logger

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_ENTITY_SUFFIX = "/entities"
API_PROVIDER_SUFFIX = "/providers"
API_CUSTOMER_SUFFIX = "/customers"
API_ENTITY_PREFIX = API_PREFIX + API_ENTITY_SUFFIX


router = APIRouter(
    prefix=API_ENTITY_PREFIX,
    tags=["entity"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def get_entity(entity_id: UUID, session: Annotated[Session, Depends(get_db)]) -> Entity:
    """
    Get an entity by its ID.
    """
    return get_by_id(session, Entity, entity_id)


@router.get(API_PROVIDER_SUFFIX, response_model=List[ProviderRead])
def read_providers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.provider_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all service providers.
    """
    return session.query(Entity) \
        .filter_by(role=EntityRoleEnum.provider) \
        .order_by(Entity.name).all()


@router.get(API_PROVIDER_SUFFIX + "/{entity_id}/testers", response_model=List[UserLookup])
def read_providers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.provider_read.name])],
    entity_id: UUID,
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all testers for the given provider ID.
    """
    testers = session.query(User) \
        .filter(and_(and_(User.provider_id == Entity.id, User.provider_id == entity_id),
                     Entity.role == EntityRoleEnum.provider)).all()
    return testers


@router.get(API_CUSTOMER_SUFFIX, response_model=List[CustomerRead])
def read_customers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.customer_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all customers.
    """
    return session.query(Entity) \
        .filter_by(role=EntityRoleEnum.customer) \
        .order_by(Entity.name).all()


@router.delete(API_PROVIDER_SUFFIX + "/{entity_id}", response_model=StatusMessage)
def delete_provider(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.provider_delete.name])],
    entity: Annotated[UUID, Depends(get_entity)],
    session: Session = Depends(get_db)
):
    """
    Deletes a provider by its ID.
    """
    if entity.role == EntityRoleEnum.provider:
        session.delete(entity)
        session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Record successfully deleted."
        )
    return StatusMessage(
        status=status.HTTP_400_BAD_REQUEST,
        severity=StatusEnum.error,
        message=f"Record was not deleted."
    )


@router.delete(API_CUSTOMER_SUFFIX + "/{entity_id}", response_model=StatusMessage)
def delete_customer(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.customer_delete.name])],
    entity: Annotated[UUID, Depends(get_entity)],
    session: Session = Depends(get_db)
):
    """
    Deletes a customer by its ID.
    """
    if entity.role == EntityRoleEnum.customer:
        session.delete(entity)
        session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Record successfully deleted."
        )
    return StatusMessage(
        status=status.HTTP_400_BAD_REQUEST,
        severity=StatusEnum.error,
        message=f"Record was not deleted."
    )


@router.post(API_PROVIDER_SUFFIX, response_model=ProviderRead)
def create_provider(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.provider_create.name])],
    entity: Annotated[ProviderCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new provider.
    """
    try:
        new = Entity(**entity.model_dump(), role=EntityRoleEnum.provider)
        session.add(new)
        session.commit()
        session.refresh(new)
        return new
    except Exception as e:
        raise InvalidDataError(str(e))


@router.post(API_CUSTOMER_SUFFIX, response_model=CustomerRead)
def create_customer(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.customer_create.name])],
    entity: Annotated[CustomerCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new customer.
    """
    try:
        new = Entity(**entity.model_dump(), role=EntityRoleEnum.customer)
        session.add(new)
        session.commit()
        session.refresh(new)
        return new
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put(API_PROVIDER_SUFFIX, response_model=ProviderRead)
def update_provider(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.provider_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[ProviderUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a provider by its ID.
    """
    try:
        return update_database_record(
            session=session,
            source=item,
            source_model=ProviderUpdate,
            query_model=Entity,
            commit=True
        )
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put(API_CUSTOMER_SUFFIX, response_model=CustomerRead)
def update_customer(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.customer_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[CustomerUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a customer by its ID.
    """
    try:
        return update_database_record(
            session=session,
            source=item,
            source_model=CustomerUpdate,
            query_model=Entity,
            commit=True
        )
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))
