#!/bin/bash

if [[ "$#" -ne 1 ]]; then
  echo "Usage: $0 <input video file>"
  exit 1
fi

input_file="$1"
base_name="${input_file%.*}"
extension="${input_file##*.}"
output_file="${base_name}_sections_removed.${extension}"
segment_file="segments.txt"
temp_list="file_list.txt"

# Clear file_list.txt to avoid appending to an old list
> "$temp_list"

mapfile -t segments < "$segment_file"

if [ "${#segments[@]}" -eq 1 ]; then
  start=$(echo "${segments[0]}" | awk '{print $1}')
  end=$(echo "${segments[0]}" | awk '{print $3}')
  ffmpeg -i "$input_file" -ss "$start" -to "$end" -c copy "$output_file"
else
  counter=1
  for i in "${!segments[@]}"; do
    start=$(echo "${segments[$i]}" | awk '{print $1}')
    end=$(echo "${segments[$i]}" | awk '{print $3}')
    segment_name="segment${counter}.${extension}"
    echo "file '$segment_name'" >> "$temp_list"
    ffmpeg -i "$input_file" -ss "$start" -to "$end" -c copy "$segment_name"
    ((counter++))
  done

  ffmpeg -f concat -safe 0 -i "$temp_list" -c copy "$output_file" >/dev/null 2>&1
  rm segment*."${extension}" "$temp_list"
fi
