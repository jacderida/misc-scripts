#!/usr/bin/env bash
#
DVD_IMAGES_S3_BUCKET_NAME="jacderida-dvd-images"
DVD_IMAGES_S3_BUCKET_URL_PREFIX="https://jacderida-dvd-images.s3.eu-west-2.amazonaws.com"

set -e

id=$(cat ../README | head -n 1 | awk -F ':' '{print $2}' | xargs)
if [[ -z $id ]]; then
  echo "Could not obtain ID from README"
fi

for file in *.jpg
do
  base=$(basename "$file" .jpg)
  converted="${base}-small.jpg"
  convert "$file" -resize 50% "$converted"
  aws s3 cp "$file" s3://$DVD_IMAGES_S3_BUCKET_NAME/$id/$file
  aws s3 cp "$converted" s3://$DVD_IMAGES_S3_BUCKET_NAME/$id/$converted
  echo "${DVD_IMAGES_S3_BUCKET_URL_PREFIX}/${id}/${file}" >> links.txt
  echo "${DVD_IMAGES_S3_BUCKET_URL_PREFIX}/${id}/${converted}" >> links.txt
done
