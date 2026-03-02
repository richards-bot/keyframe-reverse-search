import pytest

from app.models import SubmissionRecord


def test_submission_record_validation_fails_without_required_fields():
    with pytest.raises(Exception):
        SubmissionRecord.model_validate({"id": "x"})
