CHANNELS = """
query {
  linearChannelGroups {
    id
    title
    channels {
      __typename
      id
      title
      number
      tileImage {
        uri
      }
    }
  }
}
"""

LINEAR_START = """
mutation startLinearPlayback ($channelId: ID!, $deviceId: ID!) {
    startLinearPlayback(channelId: $channelId, deviceId: $deviceId) {
      __typename
      ... on LinearPlaybackSources {
... on PlaybackSources {
  playbackSource(drmType: WIDEVINE) {
    streamUri
    drmLicense {
      __typename
      licenseUri
        ... on FairplayLicense {
          certificateUri
      }
    }
    emeHeaders {
      name
      value
    }
  }
}
      }
  ... on SubscriptionNeeded {
    subscriptions {
      id
      title
    }
  }
    }
  }
"""

LINEAR_STOP = """
mutation StopLinearPlayback($channelId: ID!, $deviceId: ID!) {
    stopLinearPlayback(channelId: $channelId, deviceId: $deviceId)
}

"""
LINEAR_HEARTBEAT = """
mutation LinearPlaybackHeartbeat($channelId: ID!, $deviceId: ID!) {
    linearPlaybackHeartbeat(channelId: $channelId, deviceId: $deviceId) {
        timeToNextHeartbeat
    }
}
"""

REGISTER_DEVICE = """
    mutation RegisterDevice($registerDevice: RegisterDeviceInput) {
      registerDevice(registerDevice: $registerDevice) {
      __typename
       ... on Device {
        deviceId
        lastUsed
        registeredOn
        model
        name
      }
      ... on DeviceRegistrationLimitExceeded {
       maxDeviceLimit
      }
    }
  }
"""

USER_SUBCRIPTIONS = """
  query GetSubs {
    user {
      subscriptions {
        id
        title
      }
    }
  }
"""
