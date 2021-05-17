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

VOD_START = """
mutation StartVodPlayback($assetId: ID!, $deviceId: ID!, $playbackDevice: PlaybackDevice) {
    startVodPlayback(assetId: $assetId, deviceId: $deviceId, playbackDevice: $playbackDevice) {
      __typename
      ... on VodPlaybackSources {

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

VOD_STOP = """
mutation StopVodPlayback($assetId: ID!, $deviceId: ID!) {
    stopVodPlayback(assetId: $assetId, deviceId: $deviceId )
}
"""

VOD_HEARTBEAT = """
mutation VodPlaybackHeartbeat($assetId: ID!, $deviceId: ID!) {
  vodPlaybackHeartbeat(assetId: $assetId, deviceId: $deviceId) {
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

COLLECTION = """
  query GetCollection($collectionId: ID!) {
    collection(id: $collectionId) {
      id
      title
      tileImage {
        uri
      }
      namedFilters{
        id
        title
      }
      contentPage (
        filter: {
          onlyMyContent: true
          viewingContextsByContentType: {
            viewingContexts: [VOD,CATCHUP]
          }
        }
        sort: ALPHABETICAL
      ){
        pageInfo {
          endCursor
          hasNextPage
        }
        content {
          __typename
          ... on Title {
            id
            title
            contentTileHorizontal: tileImage(aspectRatio: 1.77) {
              uri
            }
            heroLandingWide: heroImage(aspectRatio: 1.77) {
              uri
            }
          }
          ... on Show {
            numberOfSeasons
          }
          ... on Movie {
            year
            duration
            synopsis
            asset {
              id
            }
          }
          ... on LinearChannel {
            id
            title
            contentTileHorizontal: tileImage(aspectRatio: 1.77) {
              uri
            }
          }
          ... on Collection {
            id
            title
            contentTileHorizontal: tileImage(aspectRatio: 1.77) {
              uri
            }
          }
        }
      }
    }
  }
"""
