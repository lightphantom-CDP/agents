# CDW CloudFormation — BRI SCP Mandatory Tagging

## File

- **`cdw-service-with-scp-tags.yaml`** — Full importable template with `TagSpecifications` on all 20 launch templates.

## What changed

1. **New parameters** (required at stack create/update):
   - `MandatoryTagApp`
   - `MandatoryTagGroup`
   - `MandatoryTagTim`
   - `MandatoryTagEnv`
   - `MandatoryTagKomponen`
   - `MandatoryTagBisnis`

2. **`TagSpecifications`** added to every `AWS::EC2::LaunchTemplate` with **`ResourceType: instance` only** — sufficient for the BRI SCP that denies `ec2:RunInstances` when these tags are missing on `arn:aws:ec2:::instance/*`.

3. Tags are sent on **`ec2:RunInstances`** via the launch template (SCP-friendly).

## Import to AWS CloudFormation

### Console

1. AWS Console → **CloudFormation** → **Create stack** → upload `cdw-service-with-scp-tags.yaml`.
2. Fill all existing parameters plus the six mandatory tag parameters.

### CLI (new stack)

```bash
aws cloudformation create-stack \
  --stack-name my-dwx-stack \
  --template-body file://cdw-service-with-scp-tags.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=KeyName,ParameterValue=my-key \
    ParameterKey=LogBucket,ParameterValue=my-log-bucket \
    ParameterKey=BackupBucket,ParameterValue=my-backup-bucket \
    ParameterKey=SdxS3Bucket,ParameterValue=my-sdx-bucket \
    ParameterKey=LogBucketLocation,ParameterValue=my-log-bucket/path \
    ParameterKey=BackupBucketLocation,ParameterValue=my-backup-bucket/path \
    ParameterKey=SdxStorageBaseLocation,ParameterValue=my-sdx-bucket/storage \
    ParameterKey=DBMasterUserPassword,ParameterValue='YourSecurePassword' \
    ParameterKey=MandatoryTagApp,ParameterValue=cdw \
    ParameterKey=MandatoryTagGroup,ParameterValue=data-platform \
    ParameterKey=MandatoryTagTim,ParameterValue=platform-team \
    ParameterKey=MandatoryTagEnv,ParameterValue=production \
    ParameterKey=MandatoryTagKomponen,ParameterValue=analytics \
    ParameterKey=MandatoryTagBisnis,ParameterValue=retail-banking
```

Add all other required parameters from your environment.

## Regenerate

```bash
python3 cloudformation/patch_cdw_scptags.py
```
