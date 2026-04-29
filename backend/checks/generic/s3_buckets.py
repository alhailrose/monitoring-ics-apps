"""AWS S3 checker — audits buckets for public access, versioning, and encryption."""

import logging
from botocore.exceptions import BotoCoreError, ClientError

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)


class S3BucketChecker(BaseChecker):
    report_section_title = "S3 BUCKETS"
    issue_label = "S3 security issues"
    recommendation_text = "S3 REVIEW: Block public access, enable versioning & encryption on flagged buckets"

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            s3 = session.client("s3", region_name="us-east-1")  # bucket list is global

            resp = s3.list_buckets()
            buckets_raw = resp.get("Buckets", [])

            buckets = []
            for b in buckets_raw:
                name = b["Name"]
                public = self._is_public(s3, name)
                versioning = self._get_versioning(s3, name)
                encrypted = self._is_encrypted(s3, name)
                buckets.append({
                    "name": name,
                    "public_access_blocked": not public,
                    "versioning": versioning,   # "Enabled" | "Suspended" | "Disabled"
                    "encrypted": encrypted,
                })

            public_count = sum(1 for b in buckets if not b["public_access_blocked"])
            unencrypted_count = sum(1 for b in buckets if not b["encrypted"])
            unversioned_count = sum(1 for b in buckets if b["versioning"] != "Enabled")

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "total": len(buckets),
                "public_buckets": public_count,
                "unencrypted_buckets": unencrypted_count,
                "unversioned_buckets": unversioned_count,
                "buckets": buckets,
            }

        except (BotoCoreError, ClientError) as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(exc),
            }
        except Exception as exc:
            return self._error_result(exc, profile, account_id)

    def _is_public(self, s3, bucket_name: str) -> bool:
        """Return True if the bucket has any public access (block not fully enabled)."""
        try:
            resp = s3.get_public_access_block(Bucket=bucket_name)
            cfg = resp.get("PublicAccessBlockConfiguration", {})
            return not all([
                cfg.get("BlockPublicAcls", False),
                cfg.get("IgnorePublicAcls", False),
                cfg.get("BlockPublicPolicy", False),
                cfg.get("RestrictPublicBuckets", False),
            ])
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                return True  # no block config → potentially public
            return False

    def _get_versioning(self, s3, bucket_name: str) -> str:
        try:
            resp = s3.get_bucket_versioning(Bucket=bucket_name)
            return resp.get("Status", "Disabled") or "Disabled"
        except Exception:
            return "Unknown"

    def _is_encrypted(self, s3, bucket_name: str) -> bool:
        try:
            s3.get_bucket_encryption(Bucket=bucket_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ServerSideEncryptionConfigurationNotFoundError":
                return False
            return True  # unknown — don't flag

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append(f"┌─ S3 CHECK | {results['profile']} ({results['account_id']})")
        lines.append(f"│  Buckets total     : {results['total']}")
        lines.append(f"│  Public buckets    : {results['public_buckets']}")
        lines.append(f"│  Unencrypted       : {results['unencrypted_buckets']}")
        lines.append(f"│  Without versioning: {results['unversioned_buckets']}")

        public = [b for b in results.get("buckets", []) if not b["public_access_blocked"]]
        if public:
            lines.append("│")
            lines.append("│  ⚠ Public buckets:")
            for b in public[:15]:
                lines.append(f"│    - {b['name']}")

        unenc = [b for b in results.get("buckets", []) if not b["encrypted"]]
        if unenc:
            lines.append("│")
            lines.append("│  ⚠ Unencrypted buckets:")
            for b in unenc[:15]:
                lines.append(f"│    - {b['name']}")

        issues = results["public_buckets"] + results["unencrypted_buckets"]
        lines.append(f"└─ Status: {'⚠ Issues found' if issues else '✓ All buckets compliant'}")
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        return result.get("public_buckets", 0) + result.get("unencrypted_buckets", 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines = ["", "S3 BUCKETS"]
        if errors:
            lines.append(f"Status: ERROR - {len(errors)} account(s) failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        total_public = sum(r.get("public_buckets", 0) for r in all_results.values())
        total_unenc = sum(r.get("unencrypted_buckets", 0) for r in all_results.values())
        total_buckets = sum(r.get("total", 0) for r in all_results.values())

        lines.append(f"Total buckets: {total_buckets}")
        if total_public > 0:
            lines.append(f"⚠ Public buckets: {total_public}")
            for prof, r in all_results.items():
                for b in r.get("buckets", []):
                    if not b["public_access_blocked"]:
                        lines.append(f"  * {prof} / {b['name']}")
        if total_unenc > 0:
            lines.append(f"⚠ Unencrypted buckets: {total_unenc}")
        if total_public == 0 and total_unenc == 0:
            lines.append("Status: CLEAR - All buckets compliant")
        return lines
