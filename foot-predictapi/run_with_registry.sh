#!/bin/bash

echo $GITHUB_TOKEN | docker login ghcr.io \
  --username waaou \
  --password-stdin

docker run --rm -it \
-e APP_URI=$APP_URI \
-e MODEL_ID=$MODEL_ID \
-e NEON_DATABASE_URL=$NEON_DATABASE_URL \
-e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
-e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
-e ARTIFACT_ROOT=$ARTIFACT_ROOT \
-e PORT=$PORT \
-p $PORT:$PORT \
ghcr.io/waaou/foot-predictapi:0.1.1
