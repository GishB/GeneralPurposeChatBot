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


def backlog(message) -> str:
    """save all user messages in a private chat"""
    time = datetime.now()
    connect_db().Table('user_messages_db').put_item\
    (
            Item={
                'unique_message_id': str(message.message_id) + str(message.from_user.id),
                'user_id': str(message.from_user.id),
                'text': str(message.text),
                'time-daily': time.strftime("%H:%M:%S"),
                'time-year': time.strftime("%Y-%m-%d"),
            }
    )
    return "200"

# if __name__ == "__main__":
#     backlog("200")