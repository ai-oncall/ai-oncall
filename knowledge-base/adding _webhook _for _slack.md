## Adding webhook for slack


- Go to -> https://api.slack.com/apps
- select your app , in this case its messenger-bot -> https://api.slack.com/apps/YOUR_APP_ID
- Select incoming webhook from the features side menu -> https://api.slack.com/apps/YOUR_APP_ID/incoming-webhooks?
- Select channel and enable webhook

> please note a new hook will be generated for each change in params

sample curl

```
curl --location 'https://hooks.slack.com/services/YOUR_WORKSPACE_ID/YOUR_WEBHOOK_ID/YOUR_TOKEN' \
--header 'Content-type: application/json' \
--data '{
    "text": ":60fps_parrot: :60fps_parrot: :60fps_parrot: Good Morning!",
    "channel" : "YOUR_CHANNEL_ID"
}'
```

