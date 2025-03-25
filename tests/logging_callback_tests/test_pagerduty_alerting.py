import asyncio
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.abspath("../.."))
import pytest
import llm
from llm.integrations.pagerduty.pagerduty import PagerDutyAlerting, AlertingConfig
from llm.proxy._types import UserAPIKeyAuth


@pytest.mark.asyncio
async def test_pagerduty_alerting():
    pagerduty = PagerDutyAlerting(
        alerting_args=AlertingConfig(
            failure_threshold=1, failure_threshold_window_seconds=10
        )
    )
    llm.callbacks = [pagerduty]

    try:
        await llm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "hi"}],
            mock_response="llm.RateLimitError",
        )
    except llm.RateLimitError:
        pass

    await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_pagerduty_alerting_high_failure_rate():
    pagerduty = PagerDutyAlerting(
        alerting_args=AlertingConfig(
            failure_threshold=3, failure_threshold_window_seconds=600
        )
    )
    llm.callbacks = [pagerduty]

    try:
        await llm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "hi"}],
            mock_response="llm.RateLimitError",
        )
    except llm.RateLimitError:
        pass

    await asyncio.sleep(2)

    # make 3 more fails
    for _ in range(3):
        try:
            await llm.acompletion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "hi"}],
                mock_response="llm.RateLimitError",
            )
        except llm.RateLimitError:
            pass

    await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_pagerduty_hanging_request_alerting():
    pagerduty = PagerDutyAlerting(
        alerting_args=AlertingConfig(hanging_threshold_seconds=0.0000001)
    )
    llm.callbacks = [pagerduty]

    await pagerduty.async_pre_call_hook(
        cache=None,
        user_api_key_dict=UserAPIKeyAuth(
            api_key="test",
            key_alias="test-pagerduty",
            team_alias="test-team",
            org_id="test-org",
            user_id="test-user",
            end_user_id="test-end-user",
        ),
        data={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        call_type="completion",
    )

    await llm.acompletion(
        model="gpt-4o",
        messages=[{"role": "user", "content": "hi"}],
    )

    await asyncio.sleep(1)
