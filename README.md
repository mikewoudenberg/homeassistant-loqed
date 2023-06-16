# LOQED

Integrate your LOQED Touch Smart Lock with Home Assistant. The lock instantly notifies Home Assistant of a lock state change and you can change the lock state yourself.

## Features

This integration supports:

- Detection of locks through zeroconf
- Send real-time status changes of the lock (open, unlock, lock)
- Change the lock state (open, unlock, lock).
  - Only if your lock has a fixed knob on the outside of your door, you can use the “open” lock state. If you do not have this (thus you have a handle on the outside of your door that you can push down), this command will behave as if the unlock command is sent.

## Installation

### Manual Installation

1. Copy the `loqed` folder into your custom_components folder in your hass configuration directory.
2. Restart Home Assistant.
3. Configure your LOQED lock through Configuration -> Integrations -> Add Integration.

### Installation with HACS (Home Assistant Community Store)

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the `Loqed` integration through HACS. (add this repository as a custom repository)
3. Restart Home Assistant.
4. Configure LOQED through Configuration -> Integrations -> Add Integration.

## Prerequisites

On the [LOQED personal access token website](https://integrations.production.loqed.com/personal-access-tokens), please follow the following steps:

{% details "Generate access token" %}

1. Login with your LOQED App e-mail address (you need to be admin)
2. Tap on "Create"
3. Give your personal access token a name (this will not be used further on, but we recommend something like "Home Assistant" to be able to recognize it as used by Home Assistant)
4. Tap on Save
5. Store the access token somewhere you can easily copy/paste from as you'll need them in the next step (and it will only be shown once). Note that you can use this token for setting up multiple locks.
   {% enddetails %}

{% include integrations/config_flow.md %}

Home Assistant should automatically detect your lock when your Home Assistant runs on the same network as your lock. In that case you only need to provide the selected API key when you configure the integration.

You can also set up a lock manually when for some reason it is not automatically detected. In that case you need to provide both the API Key from the previous step and the name of the Lock as it is known in the LOQED companion app.

## Services

Please see the default [lock integration page](/integrations/lock/) for the services available for the lock.

## De-installation in Loqed

First remove the integration from Home Assistant. This will take care of removing any configuration made on the lock itself for Home Assistant.

On [LOQED personal access token website](https://integrations.production.loqed.com/personal-access-tokens), please follow the following steps:

- Login with your LOQED App e-mail address (you need to be admin)
- Tap delete on the Personal Access Token you used when creating this integration.

## Debugging

It is possible to debug log the webhook calls and raw responses from the bridge API. This is done by setting up logging like below in configuration.yaml in Home Assistant. It is also possible to set the log level through a service call in UI.

```
logger:
  default: info
  logs:
    custom_components.loqed: debug
```
