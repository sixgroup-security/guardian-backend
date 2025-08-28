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

from __future__ import annotations

from fastapi import Depends, APIRouter, Security
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum
from routers.user import get_current_active_user, User
from sqlalchemy import text
from .tagging import API_TAGGING_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_MITRE_CWE_SUFFIX = "/cwe"
API_MITRE_CWE_PREFIX = API_TAGGING_PREFIX + API_MITRE_CWE_SUFFIX


router = APIRouter(
    prefix=API_MITRE_CWE_PREFIX,
    tags=["tagging"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("/weakness")
async def read_cwe_weaknesses(
    session: Session = Depends(get_db),
    _: User = Security(get_current_active_user, scopes=[ApiPermissionEnum.vulnerability_classifications_read.name]),
):
    """
    Read all VRTs.
    """
    sql = """
    SELECT json_agg(
        json_build_object(
            'id', b.id,
            'cwe_id', b.cwe_id,
            'name', b.name,
            'version', b.version,
            'status', CASE
                        WHEN w.status IS NULL THEN NULL
                        WHEN w.status = 'draft' THEN 10
                        WHEN w.status = 'stable' THEN 20
                        WHEN w.status = 'deprecated' THEN 30
                        WHEN w.status = 'incomplete' THEN 40
                        ELSE -1
                    END,
            'mapping', CASE
                        WHEN b.mapping IS NULL THEN NULL
                        WHEN b.mapping = 'allowed' THEN 10
                        WHEN b.mapping = 'prohibited' THEN 20
                        WHEN b.mapping = 'discouraged' THEN 30
                        WHEN b.mapping = 'allowed_with_review' THEN 40
                        ELSE -1
                    END,
            'abstraction', CASE
                        WHEN w.abstraction IS NULL THEN NULL
                        WHEN w.abstraction = 'base' THEN 10
                        WHEN w.abstraction = 'variant' THEN 20
                        WHEN w.abstraction = 'class_' THEN 30
                        ELSE -1
                    END,
            'description', w.description,
            'views', cweview.views,
            'categories', cwecategory.categories
        )
    )
    FROM cwebase b
    INNER JOIN cweweakness w ON b.id = w.id
    LEFT JOIN (
        SELECT
            s.id AS cwebase_id,
            json_agg(
                json_build_object(
                    'id', d.id,
                    'cwe_id', d.cwe_id,
                    'name', d.name,
                    'label', CONCAT('CWE-', d.cwe_id, ' - ', d.name)
                )
            ) AS views
        FROM cwebase s
        INNER JOIN cwerelationship r ON s.id = r.source_id AND r.nature = 'member_of_primary'
        INNER JOIN cwebase d ON d.id = r.destination_id AND d.cwe_type = 'view'
        GROUP BY s.id
    ) cweview ON cweview.cwebase_id = b.id
    LEFT JOIN (
        SELECT
            s.id AS cwebase_id,
            json_agg(
                json_build_object(
                    'id', d.id,
                    'cwe_id', d.cwe_id,
                    'name', d.name,
                    'label', CONCAT('CWE-', d.cwe_id, ' - ', d.name)
                )
            ) AS categories
        FROM cwebase s
        INNER JOIN cwerelationship r ON s.id = r.source_id AND r.nature = 'belongs_to'
        INNER JOIN cwebase d ON d.id = r.destination_id AND d.cwe_type = 'category'
        GROUP BY s.id
    ) cwecategory ON cwecategory.cwebase_id = b.id
    """
    result = session.execute(text(sql))
    weaknesses = result.scalar_one_or_none()
    return weaknesses if weaknesses else []


@router.get("/weakness/lookup")
async def read_cwe_weaknesses_lookup(
    session: Session = Depends(get_db),
    _: User = Security(get_current_active_user, scopes=[ApiPermissionEnum.vulnerability_classifications_read.name]),
):
    """
    Read all VRTs.
    """
    sql = """
    SELECT json_agg(
        json_build_object(
            'id', b.id,
            'cwe_id', CONCAT('CWE-', b.cwe_id),
            'label', CONCAT('CWE-', b.cwe_id, ' - ', b.name, ' (', REPLACE(b.mapping::text, '_', ' '), ')')
        )
    )
    FROM cwebase b
    INNER JOIN cweweakness w ON b.id = w.id
    WHERE b.mapping <> 'prohibited';
    """
    result = session.execute(text(sql))
    weaknesses = result.scalar_one_or_none()
    return weaknesses if weaknesses else []
