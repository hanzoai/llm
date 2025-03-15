#### What this does ####
#    On success + failure, log events to Supabase

from datetime import datetime
from typing import Optional, cast

import llm
from llm._logging import print_verbose, verbose_logger
from llm.types.utils import StandardLoggingPayload


class S3Logger:
    # Class variables or attributes
    def __init__(
        self,
        s3_bucket_name=None,
        s3_path=None,
        s3_region_name=None,
        s3_api_version=None,
        s3_use_ssl=True,
        s3_verify=None,
        s3_endpoint_url=None,
        s3_aws_access_key_id=None,
        s3_aws_secret_access_key=None,
        s3_aws_session_token=None,
        s3_config=None,
        **kwargs,
    ):
        import boto3

        try:
            verbose_logger.debug(
                f"in init s3 logger - s3_callback_params {llm.s3_callback_params}"
            )

            s3_use_team_prefix = False

            if llm.s3_callback_params is not None:
                # read in .env variables - example os.environ/AWS_BUCKET_NAME
                for key, value in llm.s3_callback_params.items():
                    if type(value) is str and value.startswith("os.environ/"):
                        llm.s3_callback_params[key] = llm.get_secret(value)
                # now set s3 params from llm.s3_logger_params
                s3_bucket_name = llm.s3_callback_params.get("s3_bucket_name")
                s3_region_name = llm.s3_callback_params.get("s3_region_name")
                s3_api_version = llm.s3_callback_params.get("s3_api_version")
                s3_use_ssl = llm.s3_callback_params.get("s3_use_ssl", True)
                s3_verify = llm.s3_callback_params.get("s3_verify")
                s3_endpoint_url = llm.s3_callback_params.get("s3_endpoint_url")
                s3_aws_access_key_id = llm.s3_callback_params.get(
                    "s3_aws_access_key_id"
                )
                s3_aws_secret_access_key = llm.s3_callback_params.get(
                    "s3_aws_secret_access_key"
                )
                s3_aws_session_token = llm.s3_callback_params.get(
                    "s3_aws_session_token"
                )
                s3_config = llm.s3_callback_params.get("s3_config")
                s3_path = llm.s3_callback_params.get("s3_path")
                # done reading llm.s3_callback_params
                s3_use_team_prefix = bool(
                    llm.s3_callback_params.get("s3_use_team_prefix", False)
                )
            self.s3_use_team_prefix = s3_use_team_prefix
            self.bucket_name = s3_bucket_name
            self.s3_path = s3_path
            verbose_logger.debug(f"s3 logger using endpoint url {s3_endpoint_url}")
            # Create an S3 client with custom endpoint URL
            self.s3_client = boto3.client(
                "s3",
                region_name=s3_region_name,
                endpoint_url=s3_endpoint_url,
                api_version=s3_api_version,
                use_ssl=s3_use_ssl,
                verify=s3_verify,
                aws_access_key_id=s3_aws_access_key_id,
                aws_secret_access_key=s3_aws_secret_access_key,
                aws_session_token=s3_aws_session_token,
                config=s3_config,
                **kwargs,
            )
        except Exception as e:
            print_verbose(f"Got exception on init s3 client {str(e)}")
            raise e

    async def _async_log_event(
        self, kwargs, response_obj, start_time, end_time, print_verbose
    ):
        self.log_event(kwargs, response_obj, start_time, end_time, print_verbose)

    def log_event(self, kwargs, response_obj, start_time, end_time, print_verbose):
        try:
            verbose_logger.debug(
                f"s3 Logging - Enters logging function for model {kwargs}"
            )

            # construct payload to send to s3
            # follows the same params as langfuse.py
            llm_params = kwargs.get("llm_params", {})
            metadata = (
                llm_params.get("metadata", {}) or {}
            )  # if llm_params['metadata'] == None

            # Clean Metadata before logging - never log raw metadata
            # the raw metadata can contain circular references which leads to infinite recursion
            # we clean out all extra llm metadata params before logging
            clean_metadata = {}
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    # clean llm metadata before logging
                    if key in [
                        "headers",
                        "endpoint",
                        "caching_groups",
                        "previous_models",
                    ]:
                        continue
                    else:
                        clean_metadata[key] = value

            # Ensure everything in the payload is converted to str
            payload: Optional[StandardLoggingPayload] = cast(
                Optional[StandardLoggingPayload],
                kwargs.get("standard_logging_object", None),
            )

            if payload is None:
                return

            team_alias = payload["metadata"].get("user_api_key_team_alias")

            team_alias_prefix = ""
            if (
                llm.enable_preview_features
                and self.s3_use_team_prefix
                and team_alias is not None
            ):
                team_alias_prefix = f"{team_alias}/"

            s3_file_name = llm.utils.get_logging_id(start_time, payload) or ""
            s3_object_key = get_s3_object_key(
                cast(Optional[str], self.s3_path) or "",
                team_alias_prefix,
                start_time,
                s3_file_name,
            )

            s3_object_download_filename = (
                "time-"
                + start_time.strftime("%Y-%m-%dT%H-%M-%S-%f")
                + "_"
                + payload["id"]
                + ".json"
            )

            import json

            payload_str = json.dumps(payload)

            print_verbose(f"\ns3 Logger - Logging payload = {payload_str}")

            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_object_key,
                Body=payload_str,
                ContentType="application/json",
                ContentLanguage="en",
                ContentDisposition=f'inline; filename="{s3_object_download_filename}"',
                CacheControl="private, immutable, max-age=31536000, s-maxage=0",
            )

            print_verbose(f"Response from s3:{str(response)}")

            print_verbose(f"s3 Layer Logging - final response object: {response_obj}")
            return response
        except Exception as e:
            verbose_logger.exception(f"s3 Layer Error - {str(e)}")
            pass


def get_s3_object_key(
    s3_path: str,
    team_alias_prefix: str,
    start_time: datetime,
    s3_file_name: str,
) -> str:
    s3_object_key = (
        (s3_path.rstrip("/") + "/" if s3_path else "")
        + team_alias_prefix
        + start_time.strftime("%Y-%m-%d")
        + "/"
        + s3_file_name
    )  # we need the s3 key to include the time, so we log cache hits too
    s3_object_key += ".json"
    return s3_object_key
