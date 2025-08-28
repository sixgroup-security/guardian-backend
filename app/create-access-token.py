import sys
import argparse
from io import StringIO
from dotenv import load_dotenv
# We specify the environment to be used.
load_dotenv(stream=StringIO("ENV=prod"))
from logging import getLogger
from datetime import datetime
from sqlalchemy import and_, func
from schema import SessionLocal
from schema.util import ApiPermissionEnum, ROLE_API_PERMISSIONS
from schema.user import User, UserType, TokenType
from core.idp import IdentityProviderBase

logger = getLogger(__name__)


def main(args: argparse.Namespace):
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    expiration_date = datetime.strptime(args.expiration, "%Y-%m-%d") if args.expiration else None
    scopes = [ApiPermissionEnum[item] for item in args.scopes]
    with SessionLocal() as session:
        if not (
                user := session.query(User)
                        .filter(
                            and_(
                                func.lower(User.full_name) == args.account.lower(),
                                User.type == UserType.technical
                            )
                        ).first()
        ):
            raise ValueError(f"User '{args.account}' does not exist!")
        if user.get_access_token(args.name):
            raise ValueError(f"Access token with name '{args.name}' exists already.")
        # Assess permissions
        for role in user.roles:
            info = [item.get("id", "") for item in ROLE_API_PERMISSIONS[role.name]]
            for scope in args.scopes:
                if scope not in info:
                    raise ValueError(f"User does not have permission to use scope: {scope}")
        # Validate the provided expiration date
        if expiration_date and expiration_date <= datetime.now():
            raise ValueError("Expiration time must be in the future")
        _, raw_jwt_token = IdentityProviderBase.create_token(
            session=session,
            token_name=args.name,
            user=user,
            token_type=TokenType.api,
            expires=expiration_date,
            scopes=[item.name for item in scopes]
        )
        session.commit()
        print(f"Newly created token: {raw_jwt_token}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""
        Administrative tool to creating access token for technical user accounts.

        For example to create the a PowerBI access token for a technical user account, run the following command:

        python app\\create-access-token.py -n "PowerBI Access Token" -s powerbi_application_read powerbi_application_project_mapping_read powerbi_bugbounty_read powerbi_project_read powerbi_vulnerability_read -a tpcybercontrolspowerbi
        """
    )
    parser.add_argument(
        '-n', '--name',
        type=str,
        required=True,
        help='The name of the newly created token.'
    )
    parser.add_argument(
        '-a', '--account',
        type=str,
        required=True,
        help='The account for which an access token is created.'
    )
    parser.add_argument(
        '-s', '--scopes',
        choices=[item.name for item in ApiPermissionEnum],
        required=True,
        nargs="+",
        help="The token's scope/permissions."
    )
    parser.add_argument(
        '-e', '--expiration',
        type=str,
        required=False,
        help="The token's expiration date (format: YYYY-MM-DD)."
    )

    try:
        main(parser.parse_args())
    except Exception as ex:
        logger.exception(ex)
