from typing import Any

import httpx


MONDAY_URL = "https://api.monday.com/v2"


QUERY = """
query ($board_id: ID!, $cursor: String) {
  boards(ids: [$board_id]) {
    id
    name
    columns {
      id
      title
      type
    }
    items_page(limit: 500, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          value
          type
        }
      }
    }
  }
}
"""


class MondayError(RuntimeError):
    pass


class MondayClient:
    def __init__(self, token: str):
        self.token = token

    async def _request(
        self,
        board_id: int,
        cursor: str | None = None,
    ) -> dict[str, Any]:

        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

        payload = {
            "query": QUERY,
            "variables": {
                "board_id": board_id,
                "cursor": cursor,
            },
        }

        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                MONDAY_URL,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            raise MondayError(
                f"Monday API HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        body = response.json()

        if body.get("errors"):
            raise MondayError(
                f"Monday API error: {str(body['errors'])[:1000]}"
            )

        return body["data"]

    async def get_board_items(
        self,
        board_id: int,
    ) -> list[dict[str, Any]]:

        cursor = None
        all_items: list[dict[str, Any]] = []

        column_titles: dict[str, str] = {}

        while True:
            data = await self._request(board_id, cursor)

            boards = data.get("boards") or []

            if not boards:
                raise MondayError(
                    f"Board {board_id} was not found or is inaccessible."
                )

            board = boards[0]

            # Build:
            # Monday column ID -> human-readable column title
            for column in board.get("columns", []):
                column_id = column.get("id")
                title = column.get("title")

                if column_id and title:
                    column_titles[column_id] = title

            page = board.get("items_page") or {}

            for item in page.get("items", []):
                # Add the human-readable title to every column value.
                for col in item.get("column_values", []):
                    col_id = col.get("id", "")
                    col["title"] = column_titles.get(col_id, col_id)

                all_items.append(item)

            cursor = page.get("cursor")

            if not cursor:
                break

        return all_items