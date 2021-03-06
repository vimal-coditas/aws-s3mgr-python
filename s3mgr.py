"""
##            ###########
 ##          ##        ##
  ##        ##         ##
   ##      ##############
    ##    ##
     ##  ##
      ####

AUTHOR = Vimal Paliwal <paliwalvimal1993@gmail.com>
A simple yet useful s3 library. Feel free to make changes as per your requirement.

MIT License

Copyright (c) 2017 Vimal Paliwal

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import boto3
from botocore.exceptions import ClientError

# Important Variables - Do not change the values
STD_STORAGE = "STANDARD"
STD_IA_STORAGE = "STANDARD_IA"
RRS_STORAGE = "REDUCED_REDUNDANCY"
GLACIER = "GLACIER"

PVT_ACL = "private"
PUB_ACL = "public-read"
PUB_RW_ACL = "public-read-write"

REGION = {
    "N_VIRGINIA": "us-east-1",
    "OHIO": "us-east-2",
    "N_CALIFORNIA": "us-west-1",
    "OREGON": "us-west-2",
    "MUMBAI": "ap-south-1",
    "SEOUL": "ap-northeast-2",
    "SINGAPORE": "ap-southeast-1",
    "SYDNEY": "ap-southeast-2",
    "TOKYO": "ap-northeast-1",
    "CANADA": "ca-central-1",
    "FRANKFURT": "eu-central-1",
    "IRELAND": "eu-west-1",
    "LONDON": "eu-west-2",
    "PARIS": "eu-west-3",
    "SAO_PAULO": "sa-east-1"
}

class s3mgr:
    def __init__(self, access_key="", secret_key="", profile="", region=REGION["N_VIRGINIA"]):
        if access_key == "" and secret_key == "" and profile == "":
            self.session = boto3.Session(region_name=region)
            self.s3 = self.session.client('s3')
        elif profile != "":
            self.session = boto3.Session(profile_name=profile)
            self.s3 = self.session.client('s3')
        elif access_key != "" and secret_key != "":
            self.session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
            self.s3 = self.session.client('s3')
        else:
            raise Exception("Either access key and secret or profile is required")

    def create_bucket(self, bucket, acl=PVT_ACL):
        """
        region: refer to REGION variable
        acl: PVT_ACL | PUB_ACL | PUB_RW_ACL
        """

        try:
            self.s3.create_bucket(
                Bucket=bucket,
                ACL=acl
            )

            return "0"
        except ClientError as e:
            return e.response['Error']['Code']


    def delete_bucket(self, bucket, force=False):
        """
        force = True(deletes everything inside the bucket before deleting the bucket itself) | False
        """

        try:
            if force:
                self.empty_bucket(bucket)

            self.s3.delete_bucket(
                Bucket=bucket
            )

            return "0"
        except ClientError as e:
            return e.response["Error"]["Code"]


    def empty_bucket(self, bucket):
        try:
            response = self.s3.list_objects_v2(
                Bucket=bucket
            )

            for index in range(0, response["KeyCount"]):
                self.delete_file(bucket, response["Contents"][index]["Key"])

            return "0"
        except ClientError as e:
            return e.response["Error"]["Code"]


    def create_folder(self, bucket, folder, is_private=True):
        try:
            self.s3.put_object(
                Bucket=bucket,
                Key=folder + ("/" if folder[-1:] != "/" else ""),
                ACL=PVT_ACL if is_private else PUB_ACL,
                ContentLength=0
            )
            return "0"
        except ClientError as e:
            return e.response["Error"]["Code"]


    def upload_file(self, bucket, key, file, content_type, storage, encrypt="", kms_id="", is_private=True):
        """
        file = full path of file to be uploaded
        content_type = supported MIME type
        encrypt = "AES" | "KMS"
        kms_id = kms key id
        """

        try:
            extra_args = {
                "ACL": PVT_ACL if is_private else PUB_ACL,
                "ContentType": content_type,
                "StorageClass": storage
            }
            
            if encrypt == "AES":
                extra_args["ServerSideEncryption"] = "AES256"
            elif encrypt == "KMS" and kms_id != "":
                extra_args["ServerSideEncryption"] = "aws:kms"
                extra_args["SSEKMSKeyId"] = kms_id
            else:
                raise Exception("kms_id is required for KMS encryption")

            self.s3.upload_file(
                file, bucket, key,
                ExtraArgs=extra_args
            )

            return "0"
        except ClientError as e:
            return e.response["Error"]["Code"]


    def delete_file(self, bucket, path):
        """
        path = Complete path of key including prefix(if any)
        """

        try:
            self.s3.delete_objects(
                Bucket=bucket,
                Delete={
                    "Objects": [
                        {
                            "Key": path
                        }
                    ]
                }
            )

            return "0"
        except ClientError as e:
            return e.response["Error"]["Code"]


    def list_contents(self, bucket, path="", include_subdir=True):
        """
        path = list contents of specific folder
        include_subdir = True | False(will only include content of particular folder)
        """

        path = path + ("/" if path != "" and path[-1:] != "/" else "")
        args = {
            "Bucket": bucket,
            "Prefix": path
        }
        response = {}
        response["Contents"] = []
        keyCount = 0
        while True:
            tmp = self.s3.list_objects_v2(**args)
            keyCount = keyCount + tmp["KeyCount"]
            for c in range(0, tmp["KeyCount"]):
                response["Contents"].append(tmp["Contents"][c])

            try:
                args['ContinuationToken'] = tmp['NextContinuationToken']
            except KeyError:
                break
        
        response["KeyCount"] = keyCount

        contents = []
        dirs = []
        for i in range(0, response["KeyCount"]):
            if include_subdir:
                if response["Contents"][i]["Key"][-1:] != "/":
                    contents.append(response["Contents"][i])
            else:
                if (path.count("/") == response["Contents"][i]["Key"].count("/")) & (response["Contents"][i]["Key"][-1:] != "/"):
                    contents.append(response["Contents"][i])
                elif (((path.count("/")+1) == response["Contents"][i]["Key"].count("/")) &
                        (response["Contents"][i]["Key"][0:response["Contents"][i]["Key"].find("/", response["Contents"][i]["Key"].find("/") + (-1 if path == "" else 1)) + 1] not in dirs)):
                    dirs.append(response["Contents"][i]["Key"])
                    dirs[len(dirs)-1] = dirs[len(dirs)-1][0:dirs[len(dirs)-1].find("/", dirs[len(dirs)-1].find("/") + (-1 if path == "" else 1)) + 1]

        return {
            "Files": contents,
            "Dirs": dirs
        }

    def restore_from_glacier(self, bucket, path="", include_subdir=True, days=2, restore_type="Standard"):
        """
        path = restore contents of specific folder
        include_subdir = True | False(will only include content of particular folder)
        restore_type = Standard/Bulk/Expedited
        """

        try:
            if self.is_object(bucket, path):
                try:
                    resp = self.s3.restore_object(
                        Bucket=bucket,
                        Key=path,
                        RestoreRequest={
                            'Days': days,
                            'GlacierJobParameters': {
                                'Tier': restore_type
                            }
                        }
                    )
                    print(path, "- Object restoration command sent")
                except ClientError as ce:
                    print(path, "- ", ce.response["Error"]["Message"])
            else:
                include_subdir = True
                contents = self.list_contents(bucket, path, include_subdir)
                keys = []
                r_count = 0
                for count in range(0, len(contents["Files"])):
                    if contents["Files"][count]["StorageClass"] == GLACIER:
                        r_count = r_count + 1
                        try:
                            resp = self.s3.restore_object(
                                Bucket=bucket,
                                Key=contents["Files"][count]["Key"],
                                RestoreRequest={
                                    'Days': days,
                                    'GlacierJobParameters': {
                                        'Tier': restore_type
                                    }
                                }
                            )
                            print(contents["Files"][count]["Key"], "- Object restoration command sent")
                        except ClientError as ce:
                            print(contents["Files"][count]["Key"], "- ", ce.response["Error"]["Message"])

                if r_count == 0:
                    print("No files are in glacier")
        except ClientError as e:
            return e.response["Error"]["Message"]
    
    def send_to_glacier(self, bucket, path="", include_subdir=True):
        """
        path = archive contents of specific folder
        include_subdir = True | False(will only include content of particular folder)
        """

        s3res = self.session.resource("s3")
        extra_args = {
            "StorageClass": GLACIER
        }
        try:
            if self.is_object(bucket, path):
                print(path, "- Sending to glacier")
                copy_src = {
                    "Bucket": bucket,
                    "Key": path
                }
                
                s3obj = s3res.Object(bucket, path)
                s3obj.copy(copy_src, extra_args)

                print(path, "- Sent to glacier")
            else:
                contents = self.list_contents(bucket, path, include_subdir)
                keys = []
                r_count = 0
                for count in range(0, len(contents["Files"])):
                    if contents["Files"][count]["StorageClass"] != GLACIER:
                        r_count = r_count + 1
                        key = contents["Files"][count]["Key"]
                        try:
                            print(key, "- Sending to glacier")
                            copy_src = {
                                "Bucket": bucket,
                                "Key": key
                            }
                            
                            s3obj = s3res.Object(bucket, key)
                            s3obj.copy(copy_src, extra_args)

                            print(key, "- Sent to glacier")
                        except ClientError as ce:
                            print(key, "- ", ce.response["Error"]["Message"])

                if r_count == 0:
                    print("File(s) already in glacier")
        except ClientError as e:
            return e.response["Error"]["Message"]

    def is_object(self, bucket, path=""):
        try:
            if path == "":
                return False
            else:
                resp = self.s3.get_object(
                    Bucket=bucket,
                    Key=path
                )
                # s3res = self.session.resource("s3")
                # obj_metadata = s3res.Object(bucket, path)
                # print(obj_metadata)

                return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidObjectState":
                return True
            
            return False

    def download(self, bucket, src="", dest=""):
        return 0