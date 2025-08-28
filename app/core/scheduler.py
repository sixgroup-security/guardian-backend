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

import time
import logging
import schedule
import threading
from schema import engine
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from schema.user import JsonWebToken

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


@schedule.repeat(schedule.every(5).seconds)
def clean_up_tokens():
    """
    Clean up expired tokens.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        with Session(engine) as session:
            session.query(JsonWebToken).filter(JsonWebToken.expiration <= cutoff_time).delete()
            session.commit()
    except Exception as e:
        logger.error(f"Could not clean up expired tokens: {e}")


def run_scheduler():
    """
    Runs the scheduler in a new daemon thread.
    """
    while True:
        schedule.run_pending()
        time.sleep(1)


# Start the scheduler in a new daemon thread
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()
