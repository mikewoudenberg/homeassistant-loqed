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
2. Search for and install the `Loqed` integration through HACS.
3. Restart Home Assistant.
4. Configure LOQED through Configuration -> Integrations -> Add Integration.

## Prerequisites

On the [LOQED web-app](https://app.loqed.com/API-Config/), please follow the following steps:

{% details "Generate Client ID and Client Secret" %}

1. Login with your LOQED App e-mail address (you need to be admin)
2. Tap “API Configuration tool”
3. Tap “Add new ClientId/Client Secret pair”
4. Store the ClientId and Client Secret somewhere you can easily copy/paste from as you'll need them in the next step
   {% enddetails %}

{% include integrations/config_flow.md %}

The integration setup will next give you instructions to enter the [Application Credentials](/integrations/application_credentials/) (OAuth Client ID and Client Secret) and authorize Home Assistant to access your account and lock(s).

{% details "OAuth and Device Authorization steps" %}

1. The first step shows a login page

2. Login with your (admin) LOQED credentials

3. LOQED will now ask you which Lock you want to setup. Select the one you want to setup

4. Either create an API key or use an existing one

5. Click `Finish` to return to Home Assistant

6. You may close the window, and return back to Home Assistant where you should see a _Success!_ message from Home Assistant.

{% enddetails %}

## Services

Please see the default [lock integration page](/integrations/lock/) for the services available for the lock.

## De-installation in Loqed

First remove the integration from Home Assistant. This will take care of removing any configuration made on the lock itself for Home Assistant.

On [LOQED web-app](https://app.loqed.com/API-Config/), please follow the following steps:

- Login with your LOQED App e-mail address (you need to be admin)
- Tap “API Configuration tool”
- Delete the Client Id / Client Secret pair you created for this integration.

## Debugging

It is possible to debug log the webhook calls and raw responses from the bridge API. This is done by setting up logging like below in configuration.yaml in Home Assistant. It is also possible to set the log level through a service call in UI.

```
logger:
  default: info
  logs:
    custom_components.loqed: debug
```
