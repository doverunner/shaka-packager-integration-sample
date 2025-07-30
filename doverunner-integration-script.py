import sys
import os
import subprocess
import argparse
import base64
import shlex

# Add the path of cpix-api-client to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
client_path = os.path.join(current_dir, 'cpix-api-client', 'python', 'src')
sys.path.append(client_path)

PACKAGER_BIN = 'packager-win-x64.exe'

from cpix_client import CpixClient
from drm_type import DrmType
from encryption_scheme import EncryptionScheme
from track_type import TrackType

FAIRPLAY_PSSH = "00000020707373680000000029701FE43CC74A348C5BAE90C7439A4700000000"
# DoveRunner KMS URL
KMS_URL = "https://drm-kms.doverunner.com/v2/cpix/pallycon/getKey/"


class CustomArgumentParser(argparse.ArgumentParser):
    def format_usage(self):
        return "usage: %(prog)s [options] [Shaka options]\n\n" % {'prog': self.prog}

    def format_help(self):
        help_text = super().format_help()
        usage_line = self.format_usage()

        description_start = help_text.find(self.description)
        if description_start != -1:
            # Replace everything before the description with the custom usage line
            modified_help = usage_line + help_text[description_start:]
        else:
            modified_help = help_text.replace(help_text.split('\n')[0], usage_line.strip())

        return modified_help


def parse_arguments():
    parser = CustomArgumentParser(description="Sample script for integrating DoveRunner CPIX with Shaka packager")
    parser.add_argument("--enc_token", required=True,
                        help="KMS token used for CPIX API communication with KMS")
    parser.add_argument("--content_id", required=True, help="Content ID")
    parser.add_argument("--drm_type", required=True,
                        help="DRM Type(s) separated by comma. Options: widevine, playready, fairplay")
    parser.add_argument("--encryption_scheme", default='cenc',
                        help="Encryption Scheme. Options: cenc, cbc1, cens, cbcs (default: cenc)")
    parser.add_argument("--track_type", default='all_tracks',
                        help="Track Type(s) separated by comma. Options: all_tracks, audio, sd, hd, uhd1, uhd2 (default: all_tracks)")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Parse args for DoveRunner first
    args, remaining = parser.parse_known_args()

    # Add args for Shaka packager to shaka_args
    args.shaka_args = remaining

    return args


def parse_flag_enum(enum_class, value_str):
    values = [v.strip().upper() for v in value_str.split(',')]
    result = enum_class(0)
    for value in values:
        if value not in enum_class.__members__:
            raise ValueError(f"Invalid {enum_class.__name__}: {value}")
        result |= enum_class[value]
    return result


def uuid_to_hex(uuid_string):
    return uuid_string.replace('-', '')


def base64_to_hex(base64_string):
    return base64.b64decode(base64_string).hex()


# Get key information using the CPIX client module
def get_key_info(enc_token, content_id, drm_types, encryption_scheme, track_types):
    kms_url_with_token = f"{KMS_URL}{enc_token}"
    client = CpixClient(kms_url_with_token)
    try:
        if TrackType.ALL_TRACKS in track_types:
            track_types = TrackType.ALL_TRACKS  # single key

        content_key_info = client.get_content_key_info_from_doverunner_kms(
            content_id,
            drm_types,
            encryption_scheme,
            track_types
        )
        return content_key_info
    except Exception as e:
        print(f"Failed to get key information: {e}")
        print(f"Error type: {type(e).__name__}")
        return None


def run_shaka_packager(content_key_info, shaka_args, drm_types, encryption_scheme, track_types, track_types_as_labels):
    if not content_key_info or not content_key_info.multidrm_infos:
        print("No valid key information.")
        return

    keys = []
    pssh = set()
    iv = None

    for key_info in content_key_info.multidrm_infos:
        # Matches the label value and track type entered by the user.
        label = "" if TrackType.ALL_TRACKS in track_types \
            else next((track_label
                       for track_label in track_types_as_labels if track_label.upper() == key_info.track_type), "")
        kid = uuid_to_hex(key_info.key_id)
        key = base64_to_hex(key_info.key)
        keys.append(f"label={label}:key_id={kid}:key={key}")

        if iv is None and key_info.iv:
            iv = base64_to_hex(key_info.iv)

        if DrmType.WIDEVINE in drm_types and key_info.widevine_pssh:
            pssh.add(base64_to_hex(key_info.widevine_pssh))
        if DrmType.PLAYREADY in drm_types and key_info.playready_pssh:
            pssh.add(base64_to_hex(key_info.playready_pssh))
        if DrmType.FAIRPLAY in drm_types:
            pssh.add(FAIRPLAY_PSSH)
            # key_info also has fairplay_hls_key_uri data, but we don't set it to --hls_key_uri option.
            # because we can just use the key uri that Shaka generates internally for multi-key.

    command = [
        PACKAGER_BIN,
        "--enable_raw_key_encryption",
        "--keys", ','.join(keys),
        "--protection_scheme", encryption_scheme.name.lower()
    ]

    if iv and DrmType.FAIRPLAY in drm_types:
        command.extend(["--iv", iv])

    if pssh:
        command.extend(["--pssh", ''.join(pssh)])

    # Add all remaining shaka_args to the command
    command.extend(shaka_args)

    # print("Created Shaka Packager final command:")
    # print(" ".join(shlex.quote(arg) for arg in command))

    try:
        subprocess.run(command, check=True)
        print("Packaging complete.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running Shaka Packager")
        # print(f"An error occurred while running Shaka Packager: {e}")


if __name__ == "__main__":
    args = parse_arguments()

    try:
        drm_types = parse_flag_enum(DrmType, args.drm_type.upper())
        track_types = parse_flag_enum(TrackType, args.track_type.upper())
        encryption_scheme = EncryptionScheme[args.encryption_scheme.upper()]
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    key_info = get_key_info(args.enc_token, args.content_id, drm_types, encryption_scheme, track_types)
    track_types_as_labels = [label.strip() for label in args.track_type.split(',')]

    if key_info:
        run_shaka_packager(key_info, args.shaka_args, drm_types, encryption_scheme, track_types, track_types_as_labels)
    else:
        print("Failed to get key information. Exit the program.")
