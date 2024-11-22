# Quickstart guide for getting your own bot instance running

## Discord setup

### Server setup

You'll need several channels on your server, basically something like this:

 - bot command channel
 - sonar log channel
 - special log channel (will be populated with s-rank snipes)
 - bot technical log channel
 - 8 Dawntrail channels
 - 8 Endwalker channels
 - 8 Shadowbringers channels

In addition you can make another channel where you make a webhook that will receive train advertisements from your test bot instance.

### Discord bot setup

See [this](https://discordpy.readthedocs.io/en/stable/discord.html) guide.

## Bot config setup

Example of config file is at config.yaml.example, copy this to config.yaml.

Fill up Discord token and log channels under discord part. 

If you have Sonar API access, fill the information under sonar part, otherwise set enable to False.

Fill any webhooks to webhooks part. Data that is needed under roles is the role id of any role that would be pinged for that expansion. Use 1 if you don't want a role ping or 0 if you don't want messages at all for that expansion.

In worlds part, important stuff are channel ids (you created these channels in Server setup part) and spreadsheet locations for the different worlds and expansions.