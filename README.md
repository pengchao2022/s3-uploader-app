# s3-uploader-app
python program




## Usage

bukect policy

```shell
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::amazon-s3-maxwell-0521/*"
        }
    ]
}

```