# Shaka Packager Integration Sample
Python sample script for DRM packaging integration using Shaka Packager and DoveRunner CPIX client



## Overview

This script facilitates the process of encrypting media content using various DRM systems (Widevine, PlayReady, FairPlay) by leveraging DoveRunner's key management service and Shaka Packager's encryption capabilities.



## Prerequisites

- Python 3.6+

- DoveRunner CPIX API client module (download project from [github](https://github.com/doverunner/cpix-api-client))

- Shaka Packager (download binary from [github](https://github.com/shaka-project/shaka-packager/releases/tag/v3.2.0))




## Installation

1. Clone this repository:
   - `git clone https://github.com/doverunner/shaka-packager-integration-sample`

2. Navigate to the project directory:

3. Clone the DoveRunner CPIX API client project to the same path as the script.
   - `git clone https://github.com/doverunner/cpix-api-client.git`


4. Download and place the Shaka Packager executable binary in the same directory as the script.
   - The current sample script uses 'packager-win-x64.exe' as an example for Windows versions.



## Usage

Run the script with the following command-line arguments:

`python3 doverunner-integration-script.py --enc_token <your enc-token> --content_id <content id> --drm_type <drm types> [options] [shaka_packager_args]`

### Required Arguments:

- `--enc_token`: KMS token for CPIX API communication with DoveRunner KMS
- `--content_id`: Content ID
- `--drm_type`: DRM Type(s) separated by comma (widevine, playready, fairplay)

### Optional Arguments:

- `--encryption_scheme`: Encryption scheme (cenc, cbc1, cens, cbcs; default: cenc)
- `--track_type`: Track Type(s) separated by comma (all_tracks, audio, sd, hd, uhd1, uhd2; default: all_tracks)

### Shaka Packager Arguments:

All arguments except the ones above will be passed directly to Shaka Packager.



## Example

`python3 doverunner-integration-script.py --enc_token your-enc-token --content_id movie123 --drm_type widevine,playready 'in=h264_720p.mp4,stream=video,init_segment=output/video/init.mp4,segment_template=output/video/$Number$.m4s' 'in=h264_720p.mp4,stream=audio,init_segment=output/audio/init.mp4,segment_template=output/audio/$Number$.m4s' --generate_static_live_mpd --mpd_output output/stream.mpd --clear_lead 0 `



## Notes

- The script will retrieve key information from DoveRunner's KMS using the provided token and content ID.
- It will then use these keys to construct a Shaka Packager command for content encryption.
- The encrypted content will be output according to the Shaka Packager arguments provided.



## References

- https://docs.doverunner.com/content-security/multi-drm/packaging/cpix-api/
- https://github.com/doverunner/cpix-api-client
- https://github.com/shaka-project/shaka-packager
