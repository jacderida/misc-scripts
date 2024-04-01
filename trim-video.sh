#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <video_file> <end_time>"
    exit 1
fi

VIDEO_FILE="$1"
END_TIME="$2"

OUTPUT_FILE="trimmed_${VIDEO_FILE}"

ffmpeg -i "${VIDEO_FILE}" -to "${END_TIME}" -c copy "${OUTPUT_FILE}"

echo "Trimmed video saved as ${OUTPUT_FILE}"
