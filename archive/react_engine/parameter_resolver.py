"""Resolves parameter references to actual values from context."""

import re
from typing import Any, Dict, Optional
from .models import ExecutionContext, StructuredObservation


class ParameterResolver:
    """Resolves placeholders like '<step X>' to actual values."""

    STEP_REF_PATTERN = re.compile(r'<step[_\s]?(\d+)[^>]*>', re.IGNORECASE)
    PREVIOUS_PATTERN = re.compile(r'<(previous|이전|최근)[^>]*>', re.IGNORECASE)

    def resolve(self, parameters: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Attempt to resolve placeholder patterns."""
        resolved = {}

        for key, value in parameters.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string(value, context)
            elif isinstance(value, list):
                resolved[key] = [self._resolve_string(v, context) if isinstance(v, str) else v
                                for v in value]
            else:
                resolved[key] = value

        return resolved

    def _resolve_string(self, value: str, context: ExecutionContext) -> str:
        """Try to resolve a single string value."""
        # Pattern: "<step 1>" or "<step 1 result>"
        match = self.STEP_REF_PATTERN.search(value)
        if match:
            step_id = int(match.group(1))
            return self._get_value_from_step(step_id, context)

        # Pattern: "<previous>" or "<이전 단계>"
        if self.PREVIOUS_PATTERN.search(value):
            if context.structured_observations:
                obs = context.structured_observations[-1]
                if obs.items and "id" in obs.items[0]:
                    return obs.items[0]["id"]

        return value  # Can't resolve, return as-is

    def _get_value_from_step(self, step_id: int, context: ExecutionContext) -> str:
        """Extract useful value from step result."""
        obs = next((o for o in context.structured_observations if o.step_id == step_id), None)
        if not obs:
            return f"<step {step_id} not found>"

        # Return first ID found
        ids = obs.get_ids()
        if ids:
            return ids[0]

        return f"<no ID in step {step_id}>"