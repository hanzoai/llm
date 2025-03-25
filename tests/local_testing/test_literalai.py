import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

import asyncio
import logging

import pytest

import llm
from llm._logging import verbose_logger
from llm.integrations.literal_ai import LiteralAILogger

verbose_logger.setLevel(logging.DEBUG)

llm.set_verbose = True


@pytest.mark.asyncio
async def test_literalai_queue_logging():
    try:
        # Initialize LiteralAILogger
        test_literalai_logger = LiteralAILogger()

        llm.callbacks = [test_literalai_logger]
        test_literalai_logger.batch_size = 6
        llm.set_verbose = True

        # Make multiple calls to ensure we don't hit the batch size
        for _ in range(5):
            response = await llm.acompletion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test message"}],
                max_tokens=10,
                temperature=0.2,
                mock_response="This is a mock response",
            )

        await asyncio.sleep(3)

        # Check that logs are in the queue
        assert len(test_literalai_logger.log_queue) == 5

        # Now make calls to exceed the batch size
        for _ in range(3):
            await llm.acompletion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test message"}],
                max_tokens=10,
                temperature=0.2,
                mock_response="This is a mock response",
            )

        # Wait a short time for any asynchronous operations to complete
        await asyncio.sleep(1)

        print(
            "Length of literalai log queue: {}".format(
                len(test_literalai_logger.log_queue)
            )
        )
        # Check that the queue was flushed after exceeding batch size
        assert len(test_literalai_logger.log_queue) < 5

        # Clean up
        for cb in llm.callbacks:
            if isinstance(cb, LiteralAILogger):
                await cb.async_httpx_client.client.aclose()

    except Exception as e:
        pytest.fail(f"Error occurred: {e}")
