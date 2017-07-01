#!/bin/bash

# Get Login Session from AWS ECR & Execute
output=$(aws --profile datapunks ecr get-login --region us-east-1 ) && $output
docker build -t casablanca .
docker tag casablanca:latest 146563464137.dkr.ecr.us-east-1.amazonaws.com/casablanca:latest
docker push 146563464137.dkr.ecr.us-east-1.amazonaws.com/casablanca:latest
cp config.json ~/Dropbox/stuff/creds/casablanca/config.json
echo "the docker build is complete"