import aws_cdk as cdk
import boto3


def get_aws_account_id():
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()["Account"]
    return account_id


def get_aws_region():
    session = boto3.session.Session()
    region = session.region_name
    return region


def get_cdk_env():
    account_id = get_aws_account_id()
    region = get_aws_region()
    # print(f"AWS Account ID: {account_id}")
    # print(f"AWS Region: {region}")
    return cdk.Environment(account=account_id, region=region)


if __name__ == "__main__":
    # Get the AWS CLI configured Account ID and Region
    account_id = get_aws_account_id()
    print(f"AWS Account ID: {account_id}")
    region = get_aws_region()
    print(f"AWS Region: {region}")
