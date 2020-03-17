import requests


def fetch_foretold(channel_id: str) -> bytes:
    """Fetch the data from foretold.io.

    :param channel_id: Channel id (UUID)
    :param output_path: If set, writes into the path.
    :returns: None if written to a file; parsed JSON if output_path not set.
    """
    if not channel_id:
        raise ValueError("Please, set channel_id.")
    url = "https://www.foretold.io/graphql/"
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1",
        "Origin": "https://www.foretold.io",
    }
    data = {
        "query": QUERY,
        "variables": {
            "channelId": channel_id,
            "first": 500,
            "order": [
                {"field": "stateOrder", "direction": "ASC"},
                {"field": "refreshedAt", "direction": "DESC"},
            ],
        },
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Error fetching data, status code: {response.status_code}")
    return response.content


QUERY = """query measurables(
  $measurableIds: [String!]
  $states: [measurableState!]
  $channelId: String
  $seriesId: String
  $creatorId: String
  $first: Int500
  $last: Int500
  $after: Cursor
  $before: Cursor
  $order: [OrderMeasurables]
) {
  measurables(
    measurableIds: $measurableIds
    states: $states
    channelId: $channelId
    seriesId: $seriesId
    creatorId: $creatorId
    first: $first
    last: $last
    after: $after
    before: $before
    order: $order
  ) {
    total
    pageInfo {
      hasPreviousPage
      hasNextPage
      startCursor
      endCursor
      __typename
    }
    edges {
      node {
        id
        labelCustom
        valueType
        measurementCount
        measurerCount
        labelSubject
        labelProperty
        state
        labelOnDate
        stateUpdatedAt
        expectedResolutionDate
        previousAggregate {
          id
          valueText
          value {
            floatCdf {
              xs
              ys
              __typename
            }
            floatPoint
            percentage
            binary
            unresolvableResolution
            comment
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}"""
