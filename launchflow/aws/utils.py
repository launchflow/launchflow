import dataclasses


@dataclasses.dataclass
class ARNInfo:
    service: str
    region: str
    account: str


def parse_arn(arn: str):
    # http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
    _, _, service, region, account = arn.split(":", 4)
    return ARNInfo(service, region, account)
