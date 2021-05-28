CHANNELS = """
query getChannels($from: DateTime!, $to: DateTime!) {
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
      slots(from: $from to: $to) {
        start
        programme {
          ... on Title {
            title
          }
          ... on Episode {
            show {
              title
            }
          }
        }
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
        %s
        %s
        filter: {
          onlyMyContent: true
          viewingContextsByContentType: {
            viewingContexts: [%s]
          }
        }
        %s
        %s
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
            synopsis
            primaryGenres {
              title
            }
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
            asset {
              id
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

VOD_CATEGORIES = """
query GetBrowseCategories($excludeViewingContexts: [ViewingContext!]) {
  section(id: "browse") {
  ... on Section {
      home {
      ... on BrowseHome {
        categories(excludeViewingContexts: $excludeViewingContexts) {
            __typename
            id
            title
            tileImage {
              uri
            }
          }
        }
      }
    }
  }
}
"""

SEARCH = """
  query Search($term: String!) {
    search(term: $term) {
        results {
            __typename
            ... on Title {
              id
              title
              synopsis
              primaryGenres {
                title
              }
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
              asset {
                id
              }
            }
        }
    }
}
"""

SHOW = """
query GetShow($brandId: ID!) {
  show(id: $brandId) {
    __typename
    ...on Title {
      id
      title
      synopsis
      primaryGenres {
        title
      }
      contentTileHorizontal: tileImage(aspectRatio: 1.77) {
        uri
      }
      heroLandingWide: heroImage(aspectRatio: 1.77) {
        uri
      }
    }
    type
    numberOfSeasons
    seasons(viewingContexts: VOD) {
      id
      number
      episodes(viewingContexts: VOD) {
        ...episodeFields
      }
    }
  }
}

fragment episodeFields on Episode {
  id
  title
  number
  synopsis
  duration
  asset {
    id
  }
  image {
    uri
  }
}
"""

HOME = """
query getHome {
  section(id: "home") {
    id
    home {
      __typename
      ... on ContentHome {
        path
        hero {
          ... on Title {
            __typename
            id
            title
            synopsis
            primaryGenres {
              title
            }
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
            asset {
              id
            }
          }
        }
        groups {
          id
          title
        }
      }
    }
  }
}
"""

GROUP = """
query GetGroup($railId: ID!) {
  group(id: $railId){
    id
    title
    content {
      __typename
      ... on Title {
        __typename
        id
        title
        synopsis
        primaryGenres {
          title
        }
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
        asset {
          id
        }
      }
      ... on Collection {
        id
        title
        contentTileHorizontal: tileImage(aspectRatio: 1.77) {
          uri
        }
      }
      ... on LinearChannel {
        id
        title
        number
        tileImage {
          uri
        }
        slot {
          start
          programme {
            ... on Title {
              title
            }
            ... on Episode {
              show {
                title
              }
            }
          }
        }
      }
    }
  }
}
"""
