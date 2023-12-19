""" functions to work with database """
import os
import boto3
from datetime import datetime


def connect_db() -> boto3.resource:
    """simple connection to database on yandexcloud"""
    return boto3.resource \
            (
            'dynamodb',
            endpoint_url=os.getenv("ENDPOINT_URL"),
            region_name=os.getenv("REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )


def all_messages_db(message, time, out) -> str:
    connect_db().Table('user_messages_db').put_item \
        (
            Item={
                'unique_message_id': str(message.message_id),
                'user_id': str(message.from_user.id),
                'text': str(message.text),
                'model_outputs': out,
                'time': time,
            }
        )
    return "200"


def backlog(message, out: str = None) -> str:
    """save all user messages at your boto3 database"""
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_messages_db(message, time, out)
    return "200"
