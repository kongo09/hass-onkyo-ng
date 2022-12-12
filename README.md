[![HACS Default][hacs_shield]][hacs]
[![GitHub Latest Release][releases_shield]][latest_release]

[hacs_shield]: https://img.shields.io/static/v1.svg?label=HACS&message=Custom&style=popout&color=orange&labelColor=41bdf5&logo=HomeAssistantCommunityStore&logoColor=white
[hacs]: https://hacs.xyz/docs/default_repositories

[latest_release]: https://github.com/kongo09/hass-onkyo-ng/releases/latest
[releases_shield]: https://img.shields.io/github/release/kongo09/hass-onkyo-ng.svg?style=popout

This is a `Local Pull` integration for Onkyo and Pioneer AV receivers.
Only devices that support EISCP will work.


## Note

This integration makes an effort to improve on the Home Assistant [core onkyo integration](https://www.home-assistant.io/integrations/onkyo/). It does this as part of HACS instead of HA core due to my laziness. You're welcome to take whatever useful bits and pieces you find here and bring it into the core integration. Goal in the end is for me to retire this custom integration at some point.


## Install

* Go to HACS -> Integrations
* Click the three dots on the top right and select `Custom Repositories`
* Enter `https://github.com/kongo09/hass-onkyo-ng.git` as repository, select the category `Integration` and click Add
* A new custom integration shows up for installation (Onkyo NG) - install it
* Restart Home Assistant


## Configuration

* The integration attempts to autodiscover your receiver. Autodiscovery is based on the MAC address. Home Assistant will notify you, if that is successful. 
* Alternatively, go to Configuration -> Devices & Services
* Click `Add Integration`
* Search for `Onkyo NG` and select it
* Enter the hostname / IP address of your device
* The model type is detected automatically. You get a warning in the log, if it is not supported.

Note: `configuration.yaml` is not supported.



## Debugging

To aquire debug-logs, add the following to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.hass_onkyo_ng: debug
```

logs should now be available in `home-assistant.log`


## Usage

### Entities

The integration provides `media_player` entities for your devices which are [documented here](https://www.home-assistant.io/integrations/media_player/).

