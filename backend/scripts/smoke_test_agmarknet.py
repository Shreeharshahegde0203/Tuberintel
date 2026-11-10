from __future__ import annotations

import json

from app.services.agmarknet_service import agmarknet_service


def main() -> None:
    print("Testing direct AGMARKNET connection...")
    print()

    result = agmarknet_service.probe(
        state="Karnataka",
    )

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
