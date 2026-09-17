#!/usr/bin/env python3
"""Patch CDW CloudFormation base template with Launch Template TagSpecifications for BRI SCP compliance."""

import re
from pathlib import Path

BASE = Path(__file__).parent / "cdw-service-base.yaml"
OUT = Path(__file__).parent / "cdw-service-with-scp-tags.yaml"

PARAM_GROUP = '''    - Label:
        default: "Mandatory Tagging (SCP)"
      Parameters:
      - MandatoryTagApp
      - MandatoryTagGroup
      - MandatoryTagTim
      - MandatoryTagEnv
      - MandatoryTagKomponen
      - MandatoryTagBisnis
'''

NEW_PARAMS = '''
  MandatoryTagApp:
    Type: String
    Description: Required app tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'

  MandatoryTagGroup:
    Type: String
    Description: Required group tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'

  MandatoryTagTim:
    Type: String
    Description: Required tim tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'

  MandatoryTagEnv:
    Type: String
    Description: Required env tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'

  MandatoryTagKomponen:
    Type: String
    Description: Required komponen tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'

  MandatoryTagBisnis:
    Type: String
    Description: Required bisnis tag on ec2:RunInstances (SCP compliance)
    MinLength: '1'
'''

TAG_BLOCK = '''        TagSpecifications:
          - ResourceType: instance
            Tags:
              - Key: Name
                Value: !Sub "${{AWS::StackName}}-{name_suffix}"
              - Key: app
                Value: !Ref MandatoryTagApp
              - Key: group
                Value: !Ref MandatoryTagGroup
              - Key: tim
                Value: !Ref MandatoryTagTim
              - Key: env
                Value: !Ref MandatoryTagEnv
              - Key: komponen
                Value: !Ref MandatoryTagKomponen
              - Key: bisnis
                Value: !Ref MandatoryTagBisnis
              - Key: !Sub 'kubernetes.io/cluster/${{AWS::StackName}}-eks'
                Value: shared
              - Key: managed-by
                Value: cloudformation
'''


def main() -> None:
    content = BASE.read_text()

    if "Mandatory Tagging (SCP)" not in content:
        content = content.replace(
            '    - Label:\n        default: "IAM + KMS Configuration"\n      Parameters:\n      - RoleARN\n      - EncryptionKeyARN\n',
            '    - Label:\n        default: "IAM + KMS Configuration"\n      Parameters:\n      - RoleARN\n      - EncryptionKeyARN\n' + PARAM_GROUP,
        )

    if "MandatoryTagApp:" not in content:
        content = content.replace(
            "  RoleARN:\n    Type: String\n    Description: 'RoleARN to add to KMS Key policy as principal'\n    Default: \" \"\n\nMappings:",
            "  RoleARN:\n    Type: String\n    Description: 'RoleARN to add to KMS Key policy as principal'\n    Default: \" \"\n" + NEW_PARAMS + "\nMappings:",
        )

    asg_name_map = {}
    for m in re.finditer(
        r'  (\w+):\n    Type: AWS::AutoScaling::AutoScalingGroup.*?'
        r'- Key: Name\n          Value: !Sub "\$\{AWS::StackName\}-([^"]+)"',
        content,
        re.DOTALL,
    ):
        asg_name_map[m.group(1)] = m.group(2)

    lt_name_map: dict[str, str] = {}
    for m in re.finditer(
        r'  (\w+):\n    Type: AWS::EC2::LaunchTemplate(?:\n    Condition: \w+)?\n    Properties:.*?'
        r'ResourceName: (\w+)',
        content,
        re.DOTALL,
    ):
        lt_res, asg_res = m.group(1), m.group(2)
        suffix = asg_name_map.get(asg_res)
        if suffix:
            lt_name_map[lt_res] = suffix
        elif lt_res == "SharedServicesNodeLaunchTemplate":
            lt_name_map[lt_res] = "eks-shared-services-node"
        elif lt_res == "DevModeComputeNodeLaunchTemplate":
            lt_name_map[lt_res] = "eks-dev-mode-compute-node"

    def insert_tags(match: re.Match[str]) -> str:
        block = match.group(0)
        if "TagSpecifications:" in block:
            return block
        lt_res = match.group(1)
        suffix = lt_name_map.get(lt_res, lt_res.lower())
        tag_block = TAG_BLOCK.format(name_suffix=suffix)
        return block.replace("\n        MetadataOptions:", "\n" + tag_block + "\n        MetadataOptions:", 1)

    pattern = re.compile(
        r"  (\w+):\n    Type: AWS::EC2::LaunchTemplate(?:\n    Condition: \w+)?\n    Properties:.*?\n        MetadataOptions:",
        re.DOTALL,
    )
    content, count = pattern.subn(insert_tags, content)

    content = content.replace(
        "Description: Deploys CDW Service",
        "Description: Deploys CDW Service (with Launch Template instance TagSpecifications for BRI SCP mandatory tagging on ec2:RunInstances)",
    )

    OUT.write_text(content)
    print(f"Patched {count} launch templates -> {OUT}")


if __name__ == "__main__":
    main()
