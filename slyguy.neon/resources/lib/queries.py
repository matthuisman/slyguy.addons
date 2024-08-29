LOGIN = """
query LoginQuery($input: ConfigInput, $username: String!, $password: String!) {
    config(input: $input) {
        __typename
            videoPlayer {__typename videoCloudPlayerId videoCloudAccountId videoCloudPolicyKey}
    }
    login(email: $username, password: $password) {
        __typename 
            session {__typename token}
            name surname email
            subscription {__typename status}
    }
}
"""

CONFIG = """
query SplashConfig($input: ConfigInput) {
    config(input: $input) {
        __typename 
            session {__typename token}
            videoPlayer {__typename videoCloudPlayerId videoCloudAccountId videoCloudPolicyKey}
    }
}
"""

ACCOUNT = """
query AccountQuery {
  account {
    ...AccountFields
    __typename
  }
}

fragment AccountFields on Account {
  name
  surname
  email
  selectedProfile
  hasPin
  optIns {
    id
    text
    subscribed
    __typename
  }
  phoneNumbers {
    home
    mobile
    __typename
  }
  session {
    token
    __typename
  }
  profiles {
    ...ProfileFields
    __typename
  }
  settings {
    requirePinForSwitchProfile
    requirePinForManageProfile
    tvodPurchaseRestriction
    playbackQuality {
      ...PlaybackQualityFields
      __typename
    }
    __typename
  }
  purchases {
    totalItems
    items {
      ...PurchaseFields
      __typename
    }
    __typename
  }
  cpCustomerID
  subscription {
    ...SubscriptionInformationFields
    __typename
  }
  isNeonMigrationCompleted
  __typename
}

fragment ProfileFields on Profile {
  id
  name
  email
  isKid
  isDefault
  needToConfigure
  ageGroup
  avatar {
    uri
    id
    __typename
  }
  closedCaption
  maxRating
  mobile
  __typename
}

fragment PlaybackQualityFields on PlaybackQuality {
  wifi {
    id
    label
    description
    bitrate
    __typename
  }
  __typename
}

fragment PurchaseFields on Purchase {
  id
  profile {
    id
    name
    __typename
  }
  contentItem {
    ...ContentItemLightFields
    __typename
  }
  product {
    id
    name
    renewable
    __typename
  }
  total
  startAvailable
  endAvailable
  endViewable
  __typename
}

fragment ContentItemLightFields on ContentItem {
  id
  isRental
  ... on Title {
    id
    ldId
    path
    title
    year
    rating {
      id
      rating
      __typename
    }
    genres
    duration
    images {
      uri
      __typename
    }
    createdAt
    products {
      id
      originalPrice
      currentPrice
      name
      currency
      __typename
    }
    isComingSoon
    videoExtras {
      ...VideoExtraFields
      __typename
    }
    tile {
      image
      header
      subHeader
      badge
      contentItem {
        id
        __typename
      }
      sortValues {
        key
        value
        __typename
      }
      playbackInfo {
        status
        numberMinutesRemaining
        numberMinutesWatched
        position
        __typename
      }
      rentalInfo {
        secondsLeftToStartWatching
        secondsLeftToWatch
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Series {
    title
    ldId
    genres
    path
    products {
      id
      originalPrice
      currentPrice
      name
      currency
      __typename
    }
    seasons {
      id
      episodes {
        id
        title
        seasonNumber
        episodeNumber
        __typename
      }
      __typename
    }
    images {
      uri
      __typename
    }
    createdAt
    isComingSoon
    videoExtras {
      ...VideoExtraFields
      __typename
    }
    tile {
      image
      header
      subHeader
      badge
      contentItem {
        id
        __typename
      }
      sortValues {
        key
        value
        __typename
      }
      playbackInfo {
        status
        numberMinutesRemaining
        numberMinutesWatched
        position
        __typename
      }
      rentalInfo {
        secondsLeftToStartWatching
        secondsLeftToWatch
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Episode {
    episodeNumber
    seasonNumber
    series {
      id
      title
      path
      seasons {
        episodes {
          id
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VideoExtra {
    contentItems {
      id
      __typename
    }
    __typename
  }
  __typename
}

fragment VideoExtraFields on VideoExtra {
  id
  description
  images {
    id
    uri
    height
    width
    __typename
  }
  tile {
    image
    __typename
  }
  start
  end
  title
  videoEncodings {
    ...VideoEncodingFields
    __typename
  }
  __typename
}

fragment VideoEncodingFields on VideoEncoding {
  id
  format
  referenceId
  size
  offlineEnabled
  __typename
}

fragment SubscriptionInformationFields on SubscriptionInformation {
  currentSubscription {
    name
    sku
    endsAt
    startsAt
    price
    features
    order {
      voucherCode
      __typename
    }
    subscriptionGAType
    promotion {
      name
      price
      isSpark
      isFreeTrial
      expiration
      isBridgingOfferPromotion
      __typename
    }
    __typename
  }
  upcomingSubscription {
    name
    sku
    endsAt
    startsAt
    price
    order {
      voucherCode
      __typename
    }
    subscriptionGAType
    promotion {
      name
      price
      isSpark
      isFreeTrial
      expiration
      __typename
    }
    __typename
  }
  upcomingFinalBillSubscription {
    sku
    __typename
  }
  nextPayment {
    date
    method
    type
    price
    __typename
  }
  recentPayments {
    date
    method
    type
    price
    __typename
  }
  status
  renewalStatus
  recurringVouchers {
    orderDetails {
      productName
      voucherCode
      status
      promotion {
        endDate
        id
        amount
        isExhausted
        __typename
      }
      __typename
    }
    __typename
  }
  dcbSubscriptionInfo {
    partnerName
    __typename
  }
  __typename
}
"""

CONTENT = """
query ScreenQuery($screenId: String!, $overrides: JSON) {
  screen(id: $screenId, overrides: $overrides) {
    ...ScreenFields
    __typename
  }
}

fragment ScreenFields on Screen {
  id
  title
  templateId
  theme
  path
  components {
    ...ComponentFieldsScreen
    __typename
  }
  __typename
}

fragment ComponentFieldsScreen on Component {
  ... on Callout {
    id
    header
    description
    cta {
      text
      target
      type
      __typename
    }
    __typename
  }
  ... on Carousel {
    id
    header
    contentType
    subType
    tiles {
      ...CarouselTileFields
      __typename
    }
    __typename
  }
  ... on CategoryComponent {
    id
    items {
      id
      name
      path
      __typename
    }
    __typename
  }
  ... on Grid {
    id
    header
    contentType
    subType
    tiles {
      ...GridTileFields
      __typename
    }
    uiConfig {
      ... on GridConfig {
        sortBy {
          label
          key
          dir
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Hotspot {
    id
    slides {
      image
      header
      subHeader
      description
      primaryCta
      addMylistCta
      removeMylistCta
      copyright
      badge
      tags
      tile {
        ...CarouselTileFields
        __typename
      }
      contentItem {
        id
        ...ContentItemLightFieldsScreen
        ... on Title {
          id
          __typename
        }
        ... on Series {
          id
          __typename
        }
        ... on Screen {
          path
          __typename
        }
        ... on VideoExtra {
          contentItems {
            id
            title
            ... on Title {
              genres
              __typename
            }
            ... on Series {
              genres
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    uiConfig {
      ... on HotspotConfig {
        interval
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Markdown {
    id
    copy
    __typename
  }
  ... on HTML {
    id
    copy
    __typename
  }
  ... on VideoFeature {
    id
    copy
    extra {
      ... on VideoExtra {
        id
        tile {
          image
          __typename
        }
        contentItems {
          ...ContentItemLightFieldsScreen
          ... on Series {
            isComingSoon
            __typename
          }
          ... on Title {
            isComingSoon
            __typename
          }
          ... on Episode {
            isComingSoon
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  ... on MediaBar {
    id
    header
    description
    tagline
    layout
    extra {
      id
      tile {
        image
        __typename
      }
      __typename
    }
    image {
      uri
      __typename
    }
    __typename
  }
  ... on PromotionalTileComponent {
    id
    promotionalTiles {
      image {
        uri
        size
        name
        class
        width
        height
        __typename
      }
      header
      description
      __typename
    }
    __typename
  }
  ... on PromotionalGridComponent {
    id
    promotionalTiles {
      image {
        uri
        size
        name
        class
        width
        height
        __typename
      }
      header
      description
      __typename
    }
    __typename
  }
  ...SeriesComponentFields
  ...TitleComponentFields
  __typename
}

fragment TileFieldsScreen on Tile {
  image
  header
  subHeader
  badge
  sortValues {
    key
    value
    __typename
  }
  playbackInfo {
    status
    numberMinutesRemaining
    numberMinutesWatched
    position
    __typename
  }
  rentalInfo {
    secondsLeftToStartWatching
    secondsLeftToWatch
    __typename
  }
  __typename
}

fragment CarouselTileFields on Tile {
  ...TileFieldsScreen
  contentItem {
    ...CarouselTileContentItemFields
    __typename
  }
  __typename
}

fragment GridTileFields on Tile {
  ...TileFieldsScreen
  contentItem {
    ...ContentItemLightFieldsScreen
    __typename
  }
  __typename
}

fragment ContentItemLightFieldsScreen on ContentItem {
  id
  ... on Episode {
    id
    title
    year
    series {
      id
      title
      path
      __typename
    }
    episodeNumber
    seasonNumber
    __typename
  }
  ... on Title {
    id
    path
    title
    year
    summary
    isRental
    start
    genres
    duration
    isComingSoon
    duration
    keyart {
        uri
    }
    rating {
      rating
      __typename
    }
    createdAt
    products {
      id
      originalPrice
      currentPrice
      name
      currency
      __typename
    }
    __typename
  }
  ... on Series {
    id
    title
    genres
    path
    isRental
    keyart {
        uri
    }
    isComingSoon
    description
    __typename
  }
  ... on Screen {
    id
    path
    __typename
  }
  __typename
}

fragment CarouselTileContentItemFields on ContentItem {
  ...ContentItemLightFieldsScreen
  ... on Title {
    isComingSoon
    playable
    __typename
  }
  ... on Episode {
    isComingSoon
    __typename
  }
  __typename
}

fragment TitleComponentFields on TitleComponent {
  title {
    ...TitleFields
    __typename
  }
  __typename
}

fragment TitleFields on Title {
  id
  title
  description
  path
  summary
  isRental
  genres
  start
  end
  language
  duration
  year
  country
  images {
    uri
    width
    height
    __typename
  }
  keyart {
    uri
    __typename
  }
  rating {
    id
    rating
    advisories
    reason
    __typename
  }
  quotes {
    quote
    attribution
    __typename
  }
  actors {
    ...ActorFields
    __typename
  }
  directors {
    ...DirectorFields
    __typename
  }
  videoEncodings {
    ...VideoEncodingFields
    __typename
  }
  videoExtras {
    ...VideoExtraFields
    __typename
  }
  ratingsAndAwards {
    ...AwardRatingFields
    __typename
  }
  products {
    id
    name
    originalPrice
    currentPrice
    viewingPeriodHours
    __typename
  }
  socialLinks {
    imdbUrl
    __typename
  }
  tile {
    image
    header
    subHeader
    badge
    contentItem {
      id
      __typename
    }
    sortValues {
      key
      value
      __typename
    }
    playbackInfo {
      status
      numberMinutesRemaining
      numberMinutesWatched
      position
      __typename
    }
    rentalInfo {
      secondsLeftToStartWatching
      secondsLeftToWatch
      __typename
    }
    __typename
  }
  __typename
}

fragment ActorFields on Actor {
  id
  name
  role
  images {
    id
    uri
    height
    width
    name
    __typename
  }
  billing
  __typename
}

fragment DirectorFields on Director {
  id
  name
  role
  images {
    id
    uri
    height
    width
    name
    __typename
  }
  billing
  __typename
}

fragment VideoEncodingFields on VideoEncoding {
  id
  format
  referenceId
  size
  offlineEnabled
  __typename
}

fragment VideoExtraFields on VideoExtra {
  id
  description
  images {
    id
    uri
    height
    width
    __typename
  }
  tile {
    image
    __typename
  }
  start
  end
  title
  videoEncodings {
    ...VideoEncodingFields
    __typename
  }
  __typename
}

fragment AwardRatingFields on AwardRating {
  name
  value
  __typename
}

fragment SeriesComponentFields on SeriesComponent {
  series {
    ...SeriesFields
    __typename
  }
  __typename
}

fragment SeriesFields on Series {
  id
  title
  description
  summary
  path
  ldId
  genres
  language
  isComingSoon
  originalAirDate
  start
  end
  images {
    uri
    width
    height
    __typename
  }
  tile {
    image
    badge
    __typename
  }
  keyart {
    uri
    __typename
  }
  quotes {
    quote
    attribution
    __typename
  }
  seasons {
    ...SeasonFields
    __typename
  }
  actors {
    ...ActorFields
    __typename
  }
  products {
    id
    originalPrice
    currentPrice
    name
    currency
    __typename
  }
  directors {
    ...DirectorFields
    __typename
  }
  videoExtras {
    ...VideoExtraFields
    __typename
  }
  ratingsAndAwards {
    ...AwardRatingFields
    __typename
  }
  rating {
    ...RatingFields
    __typename
  }
  upcomingEpisodes {
    ...EpisodeFields
    __typename
  }
  socialLinks {
    imdbUrl
    __typename
  }
  tile {
    image
    header
    subHeader
    badge
    contentItem {
      id
      __typename
    }
    sortValues {
      key
      value
      __typename
    }
    playbackInfo {
      status
      numberMinutesRemaining
      numberMinutesWatched
      position
      __typename
    }
    rentalInfo {
      secondsLeftToStartWatching
      secondsLeftToWatch
      __typename
    }
    __typename
  }
  episodicTile {
    image
    header
    subHeader
    badge
    contentItem {
      id
      __typename
    }
    sortValues {
      key
      value
      __typename
    }
    playbackInfo {
      status
      numberMinutesRemaining
      numberMinutesWatched
      position
      __typename
    }
    rentalInfo {
      secondsLeftToStartWatching
      secondsLeftToWatch
      __typename
    }
    __typename
  }
  __typename
}

fragment SeasonFields on Season {
  id
  title
  description
  createdAt
  year
  seasonNumber
  episodes {
    ...EpisodeFields
    __typename
  }
  __typename
}

fragment EpisodeFields on Episode {
  id
  ldId
  title
  description
  summary
  episodeNumber
  available
  start
  end
  originalAirDate
  upcoming
  isComingSoon
  seasonNumber
  duration
  images {
    id
    uri
    __typename
  }
  actors {
    ...ActorFields
    __typename
  }
  directors {
    ...DirectorFields
    __typename
  }
  rating {
    id
    rating
    reason
    __typename
  }
  videoEncodings {
    ...VideoEncodingFields
    __typename
  }
  videoExtras {
    ...VideoExtraFields
    __typename
  }
  series {
    id
    title
    __typename
  }
  __typename
}

fragment RatingFields on Rating {
  id
  rating
  advisories
  reason
  __typename
}
"""

UPDATE_ACCOUNT = """
mutation UpdateAccount($input: AccountInput!, $pin: String) {
  account(input: $input, pin: $pin) {
    ...AccountFields
    __typename
  }
}

fragment AccountFields on Account {
  name
  surname
  email
  selectedProfile
  hasPin
  optIns {
    id
    text
    subscribed
    __typename
  }
  phoneNumbers {
    home
    mobile
    __typename
  }
  session {
    token
    __typename
  }
  profiles {
    ...ProfileFields
    __typename
  }
  settings {
    requirePinForSwitchProfile
    requirePinForManageProfile
    tvodPurchaseRestriction
    playbackQuality {
      ...PlaybackQualityFields
      __typename
    }
    __typename
  }
  purchases {
    totalItems
    items {
      ...PurchaseFields
      __typename
    }
    __typename
  }
  cpCustomerID
  subscription {
    ...SubscriptionInformationFields
    __typename
  }
  isNeonMigrationCompleted
  __typename
}

fragment ProfileFields on Profile {
  id
  name
  email
  isKid
  isDefault
  needToConfigure
  ageGroup
  avatar {
    uri
    id
    __typename
  }
  closedCaption
  maxRating
  mobile
  __typename
}

fragment PlaybackQualityFields on PlaybackQuality {
  wifi {
    id
    label
    description
    bitrate
    __typename
  }
  __typename
}

fragment PurchaseFields on Purchase {
  id
  profile {
    id
    name
    __typename
  }
  contentItem {
    ...ContentItemLightFields
    __typename
  }
  product {
    id
    name
    renewable
    __typename
  }
  total
  startAvailable
  endAvailable
  endViewable
  __typename
}

fragment ContentItemLightFields on ContentItem {
  id
  isRental
  ... on Title {
    id
    ldId
    path
    title
    year
    rating {
      id
      rating
      __typename
    }
    genres
    duration
    images {
      uri
      __typename
    }
    createdAt
    products {
      id
      originalPrice
      currentPrice
      name
      currency
      __typename
    }
    isComingSoon
    videoExtras {
      ...VideoExtraFields
      __typename
    }
    tile {
      image
      header
      subHeader
      badge
      contentItem {
        id
        __typename
      }
      sortValues {
        key
        value
        __typename
      }
      playbackInfo {
        status
        numberMinutesRemaining
        numberMinutesWatched
        position
        __typename
      }
      rentalInfo {
        secondsLeftToStartWatching
        secondsLeftToWatch
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Series {
    title
    ldId
    genres
    path
    products {
      id
      originalPrice
      currentPrice
      name
      currency
      __typename
    }
    seasons {
      id
      episodes {
        id
        title
        seasonNumber
        episodeNumber
        __typename
      }
      __typename
    }
    images {
      uri
      __typename
    }
    createdAt
    isComingSoon
    videoExtras {
      ...VideoExtraFields
      __typename
    }
    tile {
      image
      header
      subHeader
      badge
      contentItem {
        id
        __typename
      }
      sortValues {
        key
        value
        __typename
      }
      playbackInfo {
        status
        numberMinutesRemaining
        numberMinutesWatched
        position
        __typename
      }
      rentalInfo {
        secondsLeftToStartWatching
        secondsLeftToWatch
        __typename
      }
      __typename
    }
    __typename
  }
  ... on Episode {
    episodeNumber
    seasonNumber
    series {
      id
      title
      path
      seasons {
        episodes {
          id
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  ... on VideoExtra {
    contentItems {
      id
      __typename
    }
    __typename
  }
  __typename
}

fragment VideoExtraFields on VideoExtra {
  id
  description
  images {
    id
    uri
    height
    width
    __typename
  }
  tile {
    image
    __typename
  }
  start
  end
  title
  videoEncodings {
    ...VideoEncodingFields
    __typename
  }
  __typename
}

fragment VideoEncodingFields on VideoEncoding {
  id
  format
  referenceId
  size
  offlineEnabled
  __typename
}

fragment SubscriptionInformationFields on SubscriptionInformation {
  currentSubscription {
    name
    sku
    endsAt
    startsAt
    price
    features
    order {
      voucherCode
      __typename
    }
    subscriptionGAType
    promotion {
      name
      price
      isSpark
      isFreeTrial
      expiration
      isBridgingOfferPromotion
      __typename
    }
    __typename
  }
  upcomingSubscription {
    name
    sku
    endsAt
    startsAt
    price
    order {
      voucherCode
      __typename
    }
    subscriptionGAType
    promotion {
      name
      price
      isSpark
      isFreeTrial
      expiration
      __typename
    }
    __typename
  }
  upcomingFinalBillSubscription {
    sku
    __typename
  }
  nextPayment {
    date
    method
    type
    price
    __typename
  }
  recentPayments {
    date
    method
    type
    price
    __typename
  }
  status
  renewalStatus
  recurringVouchers {
    orderDetails {
      productName
      voucherCode
      status
      promotion {
        endDate
        id
        amount
        isExhausted
        __typename
      }
      __typename
    }
    __typename
  }
  dcbSubscriptionInfo {
    partnerName
    __typename
  }
  __typename
}
"""

PLAYBACK_AUTH = """
mutation PlaybackAuth($drmLevel: DrmLevel!, $os: Os!, $osVersion: String!, $contentItemId: ID!) {
  playAuth(input: {drmLevel: $drmLevel, os: $os, osVersion: $osVersion, contentItemId: $contentItemId}) {
    account_id
    ad_keys
    created_at
    maxResolution
    cue_points {
      id
      name
      type
      time
      metadata
      force_stop
      __typename
    }
    custom_fields {
      programtype
      title
      spritesheet
      ldreferenceid
      seasonnumber
      episodenumber
      __typename
    }
    description
    duration
    economics
    id
    link
    long_description
    name
    offline_enabled
    poster
    poster_sources {
      src
      __typename
    }
    published_at
    reference_id
    sources {
      ext_x_version
      type
      src
      key_systems
      profiles
      __typename
    }
    tags
    thumbnail
    thumbnail_sources {
      src
      __typename
    }
    text_tracks {
      id
      account_id
      src
      srclang
      label
      kind
      mime_type
      asset_id
      sources {
        src
        __typename
      }
      in_band_metadata_track_dispatch_type
      default
      __typename
    }
    updated_at
    drmToken
    firstPlayback {
      viewingPeriodHours
      rentalPeriodHours
      __typename
    }
    __typename
  }
}
"""

SEARCH = """
query pagedSearch($pagedSearchInput: PagedSearchInput) {
  pagedSearch(input: $pagedSearchInput) {
    facets {
      type {
        movies
        series
        rentals
        __typename
      }
      __typename
    }
    hasMore
    cursor
    tiles {
      image {
        uri
        class
        __typename
      }
      header
      subHeader
      badge
      item {
        __typename
        ... on Series {
          id
          path
          isRental
          isComingSoon
          description
          keyart {
            uri
          }
          summary
          genres
          title
          __typename
        }
        ... on Title {
          id
          path
          isRental
          isComingSoon
          description
          summary
          keyart {
            uri
          }
          title
          rating {
            rating
            __typename
          }
          year
          genres
          duration
          __typename
        }
      }
      __typename
    }
    __typename
  }
}
"""
