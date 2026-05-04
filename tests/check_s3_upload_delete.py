 
from io import BytesIO
 
from PIL import Image, ImageOps

import boto3
from auth.config import settings 
from botocore.exceptions import ClientError 
from fastapi import HTTPException, status


import os, sys,  threading
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

 
def upload_s3(filenamepath: str) -> bool:
    
    if filenamepath is  None:
         return
    s3client  = _get_s3_boto3_client()

    size  = os.path.getsize(filenamepath)
    print(f"file size: {size/1024:_.1f} KB")

    s3client.upload_file(
        filenamepath, 
        settings.s3_bucket_name, f"profile_pics/{os.path.basename(filenamepath)}",    #  3rd argument =  bucket's  object name = known  as  'key'
        ExtraArgs={"ContentType": "image/jpeg"},
        Callback=ProgressPercentage(filenamepath, size)
    ) 
    print("profile pic uploaded.")

    return  filenamepath


def delete_profilepic(filename: str | None) -> None:
        if filename:
            s3client  = _get_s3_boto3_client()
            s3client.delete_object(Bucket=settings.s3_bucket_name,  Key=f"profile_pics/{os.path.basename(filename)}")
            print("reduced to dust :(")
        return

if __name__=='__main__':
    delete_profilepic(r"C:\Users\Ahmad Mahin\Downloads\logistics-it-officer.pdf")
    # upload_s3(r"C:\Users\Ahmad Mahin\Downloads\logistics-it-officer.pdf")