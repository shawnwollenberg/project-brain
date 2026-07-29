# Project Brain website

The public site is a static, tracking-free landing page served from a private
S3 bucket through CloudFront at `https://brain.wallyweb.com`.

Infrastructure is defined in
`infrastructure/project-brain-site.yaml`. CloudFormation owns the certificate,
CloudFront distribution, origin access control, security headers, and Route 53
records. The private content bucket is retained if the stack is removed.

## Deploy

```bash
aws --profile wallyweb --region us-east-1 cloudformation deploy \
  --stack-name project-brain-site \
  --template-file infrastructure/project-brain-site.yaml \
  --no-fail-on-empty-changeset

BUCKET_NAME="$(aws --profile wallyweb --region us-east-1 cloudformation describe-stacks \
  --stack-name project-brain-site \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)"

aws --profile wallyweb s3 sync website/ "s3://${BUCKET_NAME}/" \
  --delete \
  --exclude README.md \
  --cache-control 'public,max-age=300'
```

After changing content, invalidate `/index.html` and any changed asset paths.
Avoid `/*` invalidations unless the whole site changed.
