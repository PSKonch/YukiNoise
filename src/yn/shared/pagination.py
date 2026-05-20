from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True, slots=True)
class PaginationParams:
    limit: int
    offset: int


def get_pagination_params(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)
