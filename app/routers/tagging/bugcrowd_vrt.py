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
from sqlalchemy import text
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum
from routers.user import get_current_active_user, User
from .tagging import API_TAGGING_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_BUGCROWD_VRT_SUFFIX = "/vrt"
API_BUGCROWD_VRT_PREFIX = API_TAGGING_PREFIX + API_BUGCROWD_VRT_SUFFIX


router = APIRouter(
    prefix=API_BUGCROWD_VRT_PREFIX,
    tags=["tagging"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("")
async def read_vrts(
    session: Session = Depends(get_db),
    _: User = Security(get_current_active_user, scopes=[ApiPermissionEnum.vulnerability_classifications_read.name]),
):
    """
    Read all VRTs.
    """
    sql = """
    WITH cwe AS (
        SELECT
            m.vrt_id AS vrt_id,
            json_agg(
                json_build_object(
                    'id', c.id,
                    'cwe_id', c.cwe_id,
                    'label', CONCAT('CWE-', c.cwe_id, ' - ', c.name)
                )
            ) AS cwes
        FROM vrtcwemapping m
        INNER JOIN cwebase c ON c.id = m.cwe_base_id
        GROUP BY m.vrt_id
    )
    SELECT json_agg(
        json_build_object(
            'id', b.id,
            'priority_str', CASE
                        WHEN b.priority IS NULL THEN 'Varies'
                        ELSE 'P' || b.priority
                    END,
            'category_id', c.id,
            'category_name', c.name,
            'sub_category_id', s.id,
            'sub_category_name', s.name,
            'variant_id', v.id,
            'variant_name', v.name,
            'cvss_base_score', cvss.base_score,
            'cvss_base_vector', cvss.base_vector,
            'cvss_base_severity', get_severity_value(cvss.base_severity),
            'cwes', cwe.cwes
        )
        ORDER BY b.priority
    )
    FROM vrt b
    LEFT JOIN cwe cwe ON b.id = cwe.vrt_id
    LEFT JOIN vrtcategory c ON b.category_id = c.id
    LEFT JOIN vrtsubcategory s ON b.sub_category_id = s.id
    LEFT JOIN vrtvariant v ON b.variant_id = v.id
    LEFT JOIN cvss cvss ON b.cvss_id = cvss.id;
    """
    result = session.execute(text(sql))
    weaknesses = result.scalar_one_or_none()
    return weaknesses if weaknesses else []
