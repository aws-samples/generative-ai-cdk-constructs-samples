#syntax=docker/dockerfile:1.4
FROM public.ecr.aws/docker/library/python:3.11.9-slim

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

# Set environment variables
ENV COGNITO_DOMAIN='<COGNITO_DOMAIN>'
ENV REGION='us-east-1'
ENV USER_POOL_ID='<USER_POOL_ID>'
ENV CLIENT_ID='<CLIENT_ID>'
ENV CLIENT_SECRET='<CLIENT_SECRET>'
ENV IDENTITY_POOL_ID='<IDENTITY_POOL_ID>'
ENV AUTHENTICATED_ROLE_ARN='<AUTHENTICATED_ROLE_ARN>'
ENV GRAPHQL_ENDPOINT='<GRAPHQL_ENDPOINT>'
ENV S3_INPUT_BUCKET='<S3_INPUT_BUCKET>'
ENV S3_PROCESSED_BUCKET='<S3_PROCESSED_BUCKET>'
ENV CLIENT_NAME='<CLIENT_NAME>'
ENV APP_URI='http://localhost:8501'
EXPOSE 8501
COPY . .
ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8501"]



