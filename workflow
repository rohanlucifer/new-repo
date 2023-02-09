name: pipeline

on:
  push:
    branches:
      - dev

jobs:
  pipeline:
     runs-on: ubuntu-latest
     steps:
      - name: "Checkout Repository"
        uses: actions/checkout@v2
      - uses: actions/checkout@v2
        with:
          token : ${{secrets.ACCESS_TOKEN}} 
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
             aws-secret-key-id: $AWS_ACCESS_KEY_ID
             AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY     
             AWS_DEFAULT_REGION: 'ap-southeast-1'   
             S3_BUCKET: 'install.emporio.ai/dev'
             LOCAL_PATH: 'build'
             PRE_EXECUTION_SCRIPT: '.add_variables.sh'
             
             ff





