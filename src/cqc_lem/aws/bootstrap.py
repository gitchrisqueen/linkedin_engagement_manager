import os
import re
import subprocess


def bootstrap_stacks():
    # Get the directory of this current file as base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Change directory to the base directory
    os.chdir(base_dir)

    print(f"Changed to Directory: {base_dir}")

    subprocess.run(["which", "npx"], check=False)

    subprocess.run(["nvm", "use", "v22"], check=False)

    from cqc_lem.aws.util import get_aws_account_id, get_aws_region

    account_id = get_aws_account_id()
    region = get_aws_region()

    print(f"Account ID: {account_id}")
    print(f"Region: {region}")

    if account_id and region:
        if not re.fullmatch(r'\d+', account_id) or not re.fullmatch(r'[a-z0-9-]+', region):
            raise ValueError(f"Unexpected AWS account_id or region: {account_id!r}, {region!r}")
        subprocess.run(
            ['npx', '-p', 'node@22', 'cdk', 'bootstrap', f"{account_id}/{region}"],
            check=True,
        )
    else:
        print("Could not get AWS Account ID and Region")
        subprocess.run(['npx', '-p', 'node@22', 'cdk', 'bootstrap'], check=True)


if __name__ == "__main__":
    bootstrap_stacks()
