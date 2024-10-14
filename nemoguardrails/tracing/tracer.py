# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import uuid
from typing import Optional

from nemoguardrails.eval.eval import _extract_interaction_log
from nemoguardrails.eval.models import InteractionLog, InteractionOutput
from nemoguardrails.rails.llm.config import TracingConfig
from nemoguardrails.rails.llm.options import GenerationLog, GenerationResponse
from nemoguardrails.tracing.adapters import adapter_factory
from nemoguardrails.tracing.adapters.base import InteractionLogAdapter


def new_uuid() -> str:
    return str(uuid.uuid4())


class Tracer:
    def __init__(
        self,
        input,
        response: GenerationResponse,
        config: Optional[TracingConfig] = None,
    ):
        self._interaction_output = InteractionOutput(
            id=new_uuid(), input=input[-1]["content"], output=response.response
        )
        self._generation_log = response.log
        self.adapters = []
        if self._generation_log is None:
            raise RuntimeError("Generation log is missing.")

        if config:
            self._config = config

            if config.enabled:
                adapter_configs = config.adapters
                if adapter_configs:
                    self.adapters = adapter_factory(adapter_configs)

    def generate_interaction_log(
        self,
        interaction_output: Optional[InteractionOutput] = None,
        generation_log: Optional[GenerationLog] = None,
    ) -> InteractionLog:
        """Generates an InteractionLog from the given interaction output and generation log."""
        if interaction_output is None:
            interaction_output = self._interaction_output

        if generation_log is None:
            generation_log = self._generation_log

        interaction_log = _extract_interaction_log(interaction_output, generation_log)
        return interaction_log

    def add_adapter(self, adapter: InteractionLogAdapter):
        """Adds an adapter to the tracer."""
        self.adapters.append(adapter)

    def export(self):
        """Exports the interaction log using the configured adapters."""
        interaction_log = self.generate_interaction_log()
        for adapter in self.adapters:
            adapter.transform(interaction_log)

    async def export_async(self):
        """Exports the interaction log using the configured adapters."""
        interaction_log = self.generate_interaction_log()
        tasks = [adapter.transform_async(interaction_log) for adapter in self.adapters]
        await asyncio.gather(*tasks)
