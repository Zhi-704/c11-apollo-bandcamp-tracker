"""Script for sending the PDF reports as email attachments using SES."""

import logging
import os
from os import environ as ENV
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import botocore.exceptions
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as DBConnection, cursor as DBCursor

load_dotenv()

AWS_REGION = "eu-west-2"
# The full path to the file that will be attached to the email.
ATTACHMENT = ENV["FILENAME"]
# The character encoding for the email.
CHARSET = "utf-8"


def create_ses_client(access_key: str, secret_access_key: str) -> boto3.client:
    """Creates and returns an SES client using AWS access keys."""

    try:
        return boto3.client(
            "ses",
            region_name=AWS_REGION,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_access_key,
        )
    except botocore.exceptions.ClientError as e:
        raise RuntimeError(f"Error creating SES client: {e}") from e


def get_connection() -> DBConnection:
    """Creates a database session and returns a connection object."""

    return psycopg2.connect(
        host=ENV["DB_HOST"],
        port=ENV["DB_PORT"],
        user=ENV["DB_USER"],
        password=ENV["DB_PASS"],
        database=ENV["DB_NAME"],
    )


def get_cursor(connection: DBConnection) -> DBCursor:
    """Creates and returns a cursor to execute PostgreSQL commands."""

    return connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


def get_recipients(connection: DBConnection) -> list[dict]:
    """Queries the subscriber table, returning a list of dictionaries
    containing subscriber emails and names."""

    recipients = []
    try:
        with get_cursor(connection) as cursor:
            cursor.execute("SELECT email, name FROM subscriber")
            rows = cursor.fetchall()
            recipients = [{"email": row["email"], "name": row["name"]}
                          for row in rows]
    except psycopg2.Error as e:
        logging.error("Error fetching recipients: %s", e)
    finally:
        cursor.close()
    return recipients


def send_email(
    client: boto3.client,
    sender: str,
    recipient_email: str,
    recipient_name: str,
    subject: str,
) -> None:
    """Sends an email with a PDF attachment using Amazon SES."""

    body_html = f"""\
    <html>
    <head></head>
    <body>
    <h1>Good morning, {recipient_name}.</h1>
    <p>Please see the attached file for your daily generated Bandcamp sales report.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient_email

    msg.attach(MIMEText(body_html, "html"))

    with open(ATTACHMENT, "rb") as attachment:
        part = MIMEApplication(attachment.read(), _subtype="pdf")
        part.add_header(
            "Content-Disposition", "attachment", filename=os.path.basename(ATTACHMENT)
        )
        msg.attach(part)

    try:
        response = client.send_raw_email(
            Source=sender,
            Destinations=[recipient_email],
            RawMessage={"Data": msg.as_string()},
        )
        logging.info(
            "Email sent to %s! Message ID: %s", recipient_email, response["MessageId"]
        )
    except ClientError as e:
        logging.error(
            "Error sending email to %s: %s",
            recipient_email,
            e.response["Error"]["Message"],
        )


def send_all_emails() -> None:
    """Main function to send the PDF attached to an email to all recipients."""

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    sender = f"Apollo Sales Tracker <{ENV["SES_SENDER"]}>"

    aws_access_key = str(ENV.get("ACCESS_KEY"))
    aws_secret_access_key = str(ENV.get("SECRET_ACCESS_KEY"))

    ses_client = create_ses_client(aws_access_key, aws_secret_access_key)

    conn = None
    try:
        conn = get_connection()
        subscribers = get_recipients(conn)
    except Exception as e:
        logging.error("Failed to retrieve recipients: %s", e)
        raise Exception(f"Error retrieving recipients: {e}") from e
    finally:
        if conn:
            conn.close()

    today_date = datetime.now().strftime("%Y-%m-%d")

    for subscriber in subscribers:
        subject = f"Apollo - Daily Report for {
            subscriber['name']} ({today_date})"
        send_email(ses_client, sender,
                   subscriber["email"], subscriber["name"], subject)


if __name__ == "__main__":

    send_all_emails()
