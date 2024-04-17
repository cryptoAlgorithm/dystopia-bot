import os
from io import BytesIO
from uuid import uuid4

from requests import get
import boto3
from boto3_type_annotations.s3 import Client

# Cloudflare R2 (compatibility with AWS S3)
s3: Client = boto3.client(
    's3',
    endpoint_url=os.environ['S3_ENDPOINT_URL']
)


def generate_image_and_upload(prompt: str) -> str:
    from main import client
    print('Generating image:', prompt)
    resp = client.images.generate(prompt=prompt, model='dall-e-3', quality='hd', size='1024x1024')
    uploaded_filename = f'{uuid4().hex}.png'
    s3.upload_fileobj(BytesIO(get(resp.data[0].url).content), 'dystopia', uploaded_filename)
    return os.environ['BUCKET_PUBLIC_URL'] + '/' + uploaded_filename
