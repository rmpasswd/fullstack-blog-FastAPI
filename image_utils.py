import uuid

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

import boto3
from auth.config import settings 
from botocore.exceptions import ClientError 
from fastapi import HTTPException, status
from starlette.concurrency import  run_in_threadpool

import sys,  threading
class ProgressPercentage(object):

    def __init__(self, filenamepath, size):
        self._filename = filenamepath
        self._size = size 
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()



def _get_s3_boto3_client():   #  leading _ means its a private method, cannot be reached from  outside. todo: clarify
     return boto3.client(
          "s3",
          region_name=settings.s3_region,
          aws_access_key_id=settings.s3_access_key.get_secret_value() or  None,
          aws_secret_access_key=settings.s3_secret_access_key.get_secret_value() or None

     )


def process_profile_pic(image_content: bytes) -> tuple[str, bytes, int]:
    with Image.open(BytesIO(image_content)) as original:
        img = ImageOps.exif_transpose(original)
        img = ImageOps.fit(img,(300, 300), method= Image.Resampling.LANCZOS)
        
        # some formats cannot process transparency
        if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
        output  = BytesIO()
        img.save(output,  "JPEG", quality=95, optimize=True)
        output.seek(0)
      
        # assign a random filename
        filename = f"{uuid.uuid4().hex}.jpg"

    try:
        # run_in_threadpool(_upload_s3_async(filename,  output.read(), output.getbuffer().nbytes)) # this process function is already called to a threadpool in 'users' router code.
        _upload_s3_async(filename,  output.read(), output.getbuffer().nbytes)
    except ClientError as err:
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to upload image. Trying uploading again..."
         ) from err
        
    return filename, output.read(), len(output.getvalue())

def _upload_s3_async(filename: str,  image_data: bytes, size: int) -> bool:
    
    if filename is  None:
         return
    
    s3client  = _get_s3_boto3_client()
    
    # less complicated function is s3_put_object or upload_file()
    s3client.upload_fileobj( 
        BytesIO(image_data), 
        settings.s3_bucket_name, f"profile_pics/{filename}",    #  3rd argument =  bucket's  object name = known  as  'key' in aws console.
        ExtraArgs={"ContentType": "image/jpeg"},
        Callback=ProgressPercentage(filename, size)
    ) 
    print("profile pic uploaded.")

    return


def delete_profilepic(filename: str | None) -> None:
        if filename:
            s3client  = _get_s3_boto3_client()
            s3client.delete_object(Bucket=settings.s3_bucket_name,  Key=f"profile_pics/{filename}")
            print("reduced to dust :(")
        return

