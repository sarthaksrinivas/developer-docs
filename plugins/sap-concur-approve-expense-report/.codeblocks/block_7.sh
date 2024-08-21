curl --location --request PATCH 'https://us.api.concursolutions.com/expensereports/v4/users/5026e4fe-725d-44b4-bd97-02073a65b122/context/MANAGER/reports/A2466871CCCF425B8D68/sendBack' \
--header 'Authorization: Bearer {auth_token}' \
--header 'Content-Type: application/json' \
--data '{
    "comment":"Rejecting",
    "expenseRejectedComment": "Rejecting Report through API"
}'
