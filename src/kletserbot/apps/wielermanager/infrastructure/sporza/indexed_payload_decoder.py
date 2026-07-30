from collections.abc import Mapping, Sequence

from kletserbot.shared.application.exceptions import InvalidExternalResponseError


class IndexedPayloadDecoder:
    def decode(self, raw_payload: list[object]) -> dict[str, object]:
        if not raw_payload:
            raise InvalidExternalResponseError("Indexed payload is empty")

        resolved_indexes: dict[int, object] = {}
        indexes_in_progress: set[int] = set()

        def resolve_reference(reference: object) -> object:
            if isinstance(reference, bool):
                return reference
            if isinstance(reference, int):
                return resolve_index(reference)
            return resolve_node(reference)

        def resolve_index(index: int) -> object:
            if index in resolved_indexes:
                return resolved_indexes[index]
            if index in indexes_in_progress:
                raise InvalidExternalResponseError("Indexed payload contains a cyclic reference")
            if index < 0 or index >= len(raw_payload):
                raise InvalidExternalResponseError(
                    "Indexed payload contains an out-of-range reference"
                )

            indexes_in_progress.add(index)
            resolved_value = resolve_node(raw_payload[index])
            indexes_in_progress.remove(index)
            resolved_indexes[index] = resolved_value
            return resolved_value

        def resolve_node(node: object) -> object:
            if isinstance(node, Mapping):
                if node and all(_is_indexed_key(key) for key in node):
                    resolved_mapping: dict[str, object] = {}
                    for key_token, value_reference in node.items():
                        key = resolve_index(int(str(key_token)[1:]))
                        if not isinstance(key, str):
                            raise InvalidExternalResponseError(
                                "Indexed object key did not resolve to text"
                            )
                        resolved_mapping[key] = resolve_reference(value_reference)
                    return resolved_mapping
                return {str(key): resolve_reference(value) for key, value in node.items()}
            if isinstance(node, Sequence) and not isinstance(
                node,
                (str, bytes, bytearray),
            ):
                return [resolve_reference(value) for value in node]
            return node

        decoded_payload = resolve_index(0)
        if not isinstance(decoded_payload, dict):
            raise InvalidExternalResponseError("Indexed payload root must resolve to an object")
        return decoded_payload


def _is_indexed_key(key: object) -> bool:
    return isinstance(key, str) and key.startswith("_") and key[1:].isdigit()
