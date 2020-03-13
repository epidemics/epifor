#!/bin/sh
set -eu

cd data
F=foretold_data.json
if [ $# -ne 1 ]; then
    echo "run as: $0 CHANNELL_ID"
    exit 1
fi
CH=$1

curl 'https://www.foretold.io/graphql/' -H 'Accept-Encoding: gzip, deflate, br' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Connection: keep-alive' -H 'DNT: 1' -H 'Origin: https://www.foretold.io' --data-binary '{"query":"query measurables(\n  $measurableIds: [String!]\n  $states: [measurableState!]\n  $channelId: String\n  $seriesId: String\n  $creatorId: String\n  $first: Int500\n  $last: Int500\n  $after: Cursor\n  $before: Cursor\n  $order: [OrderMeasurables]\n) {\n  measurables(\n    measurableIds: $measurableIds\n    states: $states\n    channelId: $channelId\n    seriesId: $seriesId\n    creatorId: $creatorId\n    first: $first\n    last: $last\n    after: $after\n    before: $before\n    order: $order\n  ) {\n    total\n    pageInfo {\n      hasPreviousPage\n      hasNextPage\n      startCursor\n      endCursor\n      __typename\n    }\n    edges {\n      node {\n        id\n        labelCustom\n        valueType\n        measurementCount\n        measurerCount\n        labelSubject\n        labelProperty\n        state\n        labelOnDate\n        stateUpdatedAt\n        expectedResolutionDate\n        previousAggregate {\n          id\n          valueText\n          value {\n            floatCdf {\n              xs\n              ys\n              __typename\n            }\n            floatPoint\n            percentage\n            binary\n            unresolvableResolution\n            comment\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n","variables":{"channelId":"'"$CH"'","first":500,"order":[{"field":"stateOrder","direction":"ASC"},{"field":"refreshedAt","direction":"DESC"}]}}' --compressed > $F
