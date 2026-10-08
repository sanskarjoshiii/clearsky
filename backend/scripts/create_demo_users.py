"""Create Cognito dashboard users for the deployed stack (Phase 5). Run after `deploy`.

  uv run python scripts/create_demo_users.py --officer you@team.in \
      --buyer buyer@team.in:BY01 --operator op1@team.in:B01 --operator op2@team.in:B02

Each user gets a random strong password printed ONCE here (never written to disk). Share it privately.
The user pool id is read from the CloudFormation stack outputs (default stack clearsky-dev).
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys

import boto3
from botocore.exceptions import ClientError

from clearsky.config import get_settings


def _password() -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(14))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def _pool_id(stack: str, region: str) -> str:
    cf = boto3.client("cloudformation", region_name=region)
    outputs = cf.describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])
    for o in outputs:
        if o["OutputKey"] == "UserPoolId":
            return str(o["OutputValue"])
    raise SystemExit(f"UserPoolId output not found on stack {stack}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stack", default="clearsky-dev")
    p.add_argument("--user-pool-id")
    p.add_argument("--officer", action="append", default=[], help="email (optionally email:District)")
    p.add_argument("--buyer", action="append", default=[], help="email:BUYER_ID (e.g. BY01)")
    p.add_argument("--operator", action="append", default=[], help="email:BALER_ID (e.g. B01)")
    args = p.parse_args()
    region = get_settings().aws_region
    pool = args.user_pool_id or _pool_id(args.stack, region)
    idp = boto3.client("cognito-idp", region_name=region)

    users: list[tuple[str, str, dict[str, str]]] = []
    for spec in args.officer:
        email, _, district = spec.partition(":")
        users.append((email, "officer", {"custom:district": district} if district else {}))
    for spec in args.buyer:
        email, _, buyer_id = spec.partition(":")
        if not buyer_id:
            raise SystemExit(f"--buyer needs email:BUYER_ID, got {spec}")
        users.append((email, "buyer", {"custom:buyer_id": buyer_id}))
    for spec in args.operator:
        email, _, baler_id = spec.partition(":")
        if not baler_id:
            raise SystemExit(f"--operator needs email:BALER_ID, got {spec}")
        users.append((email, "operator", {"custom:baler_id": baler_id}))
    if not users:
        p.print_help()
        return 1

    print(f"user pool {pool}")
    for email, group, attrs in users:
        attributes = [{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}]
        attributes += [{"Name": k, "Value": v} for k, v in attrs.items()]
        try:
            idp.admin_create_user(
                UserPoolId=pool, Username=email, UserAttributes=attributes, MessageAction="SUPPRESS"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "UsernameExistsException":
                raise
            idp.admin_update_user_attributes(UserPoolId=pool, Username=email, UserAttributes=attributes)
        password = _password()
        idp.admin_set_user_password(UserPoolId=pool, Username=email, Password=password, Permanent=True)
        idp.admin_add_user_to_group(UserPoolId=pool, Username=email, GroupName=group)
        extra = " ".join(f"{k.split(':')[1]}={v}" for k, v in attrs.items())
        print(f"  {group:<9} {email:<32} password: {password}  {extra}")
    print("Share each password privately. Users can't self-register (admin-only pool).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
